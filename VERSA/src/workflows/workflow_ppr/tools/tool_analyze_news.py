import logging
import os
import re
import threading
from contextlib import nullcontext
from datetime import datetime, timedelta
from typing import Dict, List

import requests
import streamlit as st
from bs4 import BeautifulSoup
from gnews import GNews
try:
    from langchain_core.tools import BaseTool
    from langchain_core.messages import HumanMessage
except ImportError:
    from langchain.tools import BaseTool
    from langchain_core.messages import HumanMessage
from langchain_community.document_loaders import WebBaseLoader

from src.common.workflow_context import get_workflow
from src.common.provider import get_chat_model, get_default_provider
from ..memory import News


class AnalyzeNews(BaseTool):
    name: str = "analyze_news"
    description: str = ("Use this tool when you want to analyze news."
                        "To use the tool, you must provide the logo name.")

    def _run(self, logo_name=None) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        try:
            logging.info(f"* End process.")
            logo_name = workflow['workflow_memory'].logo_name
            max_articles_per_topic = st.secrets['ppr']['news_analysis']['max_articles_per_topic']
            
            # for each topic, get news
            # of topic and keywords
            news_analysis = {}
            
            total_topics = len(st.secrets['ppr']['news_analysis']['topics'])
            for idx, (topic, keywords) in enumerate(st.secrets['ppr']['news_analysis']['topics'].items()):
                try:
                    spinner_ctx = st.spinner(f"({idx+1}/{total_topics}) Fetching news for {topic}...")
                except Exception:
                    spinner_ctx = nullcontext()
                with spinner_ctx:
                    news = _get_news(logo_name=logo_name, topic=topic, keywords=keywords)
                    
                    if not news:
                        continue
                    
                    news = _dedup(news)
                    
                    news = _fetch_news_content(news)

                    progress = None
                    try:
                        progress = st.progress(0.0, text="Reading news and identifying potential sales opportunities...")
                    except Exception:
                        pass
                    processed = []
                    for idx, _n in enumerate(news):
                        if progress is not None:
                            progress.progress((idx+1)/len(news), text="Reading news and identifying potential sales opportunities...")
                        is_relevent, summary = _get_news_summary(logo_name=logo_name, topic=topic, content=_n.content)
                        if is_relevent and summary:
                            _n.summary = summary
                            processed.append(_n)
                            if len(processed) >= max_articles_per_topic:
                                break
                    if progress is not None:
                        progress.empty()
                    
                    # add to news analysis
                    if processed:
                        news_analysis[topic] = processed
            self._on_success(news_analysis)
        except Exception as e:
            logging.error(f"Error while analyzing the news process:", exc_info=True)
            return self._on_error()

    def _arun(self, distributor_id: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, news_analysis) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.news_analysis = news_analysis
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = "Sucessfully analyzed news."
        return to_next.message

    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error while analyzing news."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = "Error while analyzing news."
        return to_next.message


def _parse_date(date_str: str):
    """
    Parse a date string in a specific format and convert it to 'mm/dd/yy' format.
    """
    try:
        parsed_date = datetime.strptime(date_str, "%a, %d %b %Y %H:%M:%S GMT")
        return parsed_date.strftime("%m/%d/%y")
    except ValueError:
        return None
            
def _get_news(logo_name: str, topic: str, keywords: list) -> Dict[str, List[dict]]:
    end_date = datetime.today().date()
    start_date = end_date - timedelta(days=st.secrets['ppr']['news_analysis']['days_to_lookback'])
    
    # initialize the GNews object
    google_news = GNews(language='en', country='US', start_date=start_date, end_date=end_date, max_results=5)

    # get news
    news_articles = [article for keyword in keywords for article in google_news.get_news(f"{logo_name} {keyword} {topic}")]

    return [
        News(
            date=_parse_date(news.get("published date", None)),
            title=news.get("title", None),
            url=news.get("url", None),
        )
        for news in news_articles if news and news.get("url", None)
    ]
                

def _dedup(news):
    """
    Deduplicate news based on the title and summary.
    """
    def _is_similar(title: str, seen: list) -> str:
        existing_titles = '\n'.join([f"* {x}" for x in seen])
        
        # textwrap does not work with \n join 
        instruction = f"""\
Determine if the new title refers to the same event as any existing titles.
Existing titles:
{existing_titles}

New title:
{title}
Return "true" if the new title discusses the same event as any existing title, otherwise return "false". Only include this information in your response.
Output:
"""
        return _to_prompt_bot(instruction).lower()
    progress = None
    try:
        progress = st.progress(0.0, text="Deduplicating news...")
    except Exception:
        pass
    unique = [news[0]]
    for idx, article in enumerate(news[1:]):
        if progress is not None:
            progress.progress((idx+1)/(len(news)-1), text="Deduplicating news...")
        seen = [x.title for x in unique]
        if _is_similar(article.title, seen) == 'false':
            unique.append(article)
    if progress is not None:
        progress.empty()
    return unique


def _fetch_news_content(news):
    def _fetch(_n, shared: list):
        try:
            url = _n.url
            content = WebBaseLoader(url, requests_kwargs={'timeout': 3}).load()
            
            # did not get any content
            if not content or not isinstance(content, list) or len(content) == 0:
                return
            # content[0] is the content of the page
            content = content[0].page_content
                
            # handle google news jump problem
            if "Google NewsOpening" in content:
                match = re.search(r'Google NewsOpening (https?://\S+)', content)
                if not match:
                    return
                
                url = match.group(1)
                content = WebBaseLoader(url, requests_kwargs={'timeout': 3}).load()
                if content and isinstance(content, list) and len(content) > 0:
                    content = content[0].page_content
                else:
                    return
            
            # check 404
            if any(indicator in content for indicator in ["404", "Page Not Found", "Not Found", "Error 404"]):
                return
            
            # clean and truncate content
            soup = BeautifulSoup(content, 'html.parser')
            
            content = soup.get_text(separator=' ')
            content = re.sub(r'\s+', ' ', content)
            content = content.replace('{', ' ').replace('}', ' ')
            content = content.strip()
            content = content[:5000]
            
            if not content:
                return
            else:
                _n.content = content
                shared.append(_n)
        except requests.exceptions.Timeout:
            pass
        except Exception as e:
            pass
    
    news_with_content, threads = [], []
    # multi-threaded news fetching
    for _n in news:
        
        thread = threading.Thread(target=_fetch, args=(_n, news_with_content))
        thread.start()
        threads.append(thread)
    
    for thread in threads:
        thread.join()
    
    return news_with_content


def _get_news_summary(logo_name, topic, content):
    # textwrap does not work with \n join
    instruction_generae_summary = f"""\
As a sales analyst at a company specializing in promotional products, you are preparing for a meeting with a client by reviewing news related to them across various topics. Your objective is to identify potential areas where your company can offer promotional products.

Output:
Your analysis should focus on providing a concise summary of the key points, highlight any specific events, initiatives, or announcements mentioned in the news that could be relevant for promotional product placement, emphasizing potential sales opportunities between your company and the client, Include date and location details if available. Keep the summary within 50 words.

Client:
{logo_name}

News Content:
{content}

Only provide the summaried content. Stick to the news content and avoid adding any personal opinions. Do not say this is a summary or include any other information. If you could not find any relevant information, give "none" instead.
Summary:
"""
        
    summary = _to_prompt_bot(instruction_generae_summary)    
    
    # summary is a multi-line string, and have \n, textwrap.dedent does not work with \n
    prompt_check_relevance = f"""\
You are a highly skilled sales analyst from a company specializing in promotional products. Your task is to review news related to a specific client. Your evaluation should focus on whether the news is explicitly about the {logo_name} company and whether the news content is pertinent to the client's specified topic.
When reviewing news about companies, it's important to verify the specific organization being mentioned, as company names can sometimes be similar yet refer to entirely different entities. For instance, Vanguard Renewables and The Vanguard Group are not the same company, despite the similarity in their names.

Client: {logo_name}

Topic: {topic}

News Content: {summary}

Return "true" if the news is about {logo_name} and content is a relevant, otherwise return "false". Do not include any other information.
Output:
"""

    if _to_prompt_bot(prompt_check_relevance).lower() == "false":
        return False, None
    
    return True, summary.replace('\n', ' ')
    
    
def _to_prompt_bot(instruction, use_service=False):
    """Use promptbot when in main Streamlit thread; otherwise call LLM directly (worker thread)."""
    workflow = get_workflow()
    if not workflow:
        return ""
    try:
        _ = st.session_state.promptbotservice if use_service else st.session_state.promptbot
    except (KeyError, AttributeError):
        _ = None
    if _ is not None:
        to_next = workflow["to_next_memory"]
        to_next.reset()
        to_next.message = instruction
        to_next.action = "promptbot"
        if use_service:
            st.session_state.promptbotservice()
        else:
            st.session_state.promptbot()
        return workflow["to_next_memory"].message
    try:
        provider = get_default_provider()
        llm = get_chat_model(provider, temperature=0, max_tokens=500)
        response = llm.invoke([HumanMessage(content=instruction)])
        return (response.content if hasattr(response, "content") else str(response)).strip()
    except Exception as e:
        logging.warning("Direct LLM fallback in analyze_news failed: %s", e)
        return ""


