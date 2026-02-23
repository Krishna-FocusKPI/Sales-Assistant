import logging
import textwrap

import streamlit as st
try:
    from langchain_core.tools import BaseTool
    from langchain_core.messages import HumanMessage
except ImportError:
    from langchain.tools import BaseTool
    from langchain_core.messages import HumanMessage

from src.common.workflow_context import get_workflow
from src.common.provider import get_chat_model, get_default_provider


class ValidateCategory(BaseTool):
    name: str = "validate_category"
    description: str = "Use this tool when you need to validate the category. Input to this tool should be a string that contains a category name."

    def _run(self, category: str) -> str:
        try:
            logging.info(f"* Validating category code: {category}")
            exists, valid_category = category_exist(category)
            if exists:
                return self._on_success(valid_category)
            logging.info("Unable to find a direct match for the category. Starting LLM matching process.")
            
            exists, valid_category = _infer_category(category)
            logging.info(f"* Validating category code: {category} - {exists} - {valid_category}")
            if exists:
                return self._on_success(valid_category)
            return self._on_failure(category)
        except Exception as e:
            logging.error(f"Error while validating category param-category-{category}", exc_info=True)
            return self._on_failure(category)

    def _arun(self, category: int):
        raise NotImplementedError("This tool does not support async")
        
    def _on_success(self, category: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.category = category
        if memory.visited_categories is None:
            memory.visited_categories = []
        memory.visited_categories.append(category)
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully validate the input category."
        return to_next.message

    def _on_failure(self, category: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return f"Failed to validate the input category {category}"
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"Failed to validate the input category {category}"
        return to_next.message
    
# =============================================================================
# DATA HANDLING
# =============================================================================
def category_exist(target: str):
    target = target.lower()

    # find match
    for category, alternatives in st.secrets.ppr.categories.items():
        if any(alt in target for alt in alternatives):
            return True, category
    
    return False, None


def _infer_category(category: str):
    # textwrap does not work with \n join
    categories_explaination = "\n".join([f"{category} - {categories_explaination}" for category, categories_explaination in st.secrets.ppr.categories_explanation.items()])
    
    instruction = f"""\
Please analyze the category provided by the user and find the best matching category. The input might contains a typo, a different name, which is why I couldn't find a match. If you can't find a match, please return 'none'.
        
Available Categories:
{categories_explaination}
none - if the input category or item could not fit in any of above categories

User provided category:
{category}

Your response has to be one of above available categories.
If none of the available categories match, please return 'none', otherwise return the best category in the available categories.
Do not make up a category, if you return a category, it must be one of the available categories.
Do not include any additional information in your response. Do not include your explainations in the output.        
"""

    response = _to_prompt_bot(instruction)
    logging.info(f"* Infer category response: {response}")
    return category_exist(response)

def _to_prompt_bot(instruction, use_service=False):
    """
    Resolve the instruction via LLM. In the main Streamlit thread we use promptbot.
    In the agent's worker thread (no Streamlit context), we call the LLM directly.
    """
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

    # Worker thread: no st.session_state — call LLM directly
    try:
        provider = get_default_provider()
        llm = get_chat_model(provider, temperature=0, max_tokens=500)
        response = llm.invoke([HumanMessage(content=instruction)])
        return (response.content if hasattr(response, "content") else str(response)).strip()
    except Exception as e:
        logging.warning("Direct LLM fallback for category inference failed: %s", e)
        return "none"