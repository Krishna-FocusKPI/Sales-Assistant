import copy
import logging
import os
import re
import textwrap

import numpy as np
import pandas as pd
import pandasql as ps
import streamlit as st
try:
    from langchain_core.output_parsers.json import parse_json_markdown
except ImportError:
    try:
        from langchain_core.utils.json import parse_json_markdown
    except ImportError:
        from langchain_classic.output_parsers.json import parse_json_markdown
try:
    from langchain_core.tools import BaseTool
    from langchain_core.messages import HumanMessage
except ImportError:
    from langchain.tools import BaseTool
    from langchain_core.messages import HumanMessage
from src.common.provider import get_embeddings, get_chat_model, get_default_provider
from src.common.workflow_context import get_workflow


class FilterProduct(BaseTool):
    name: str = "filter_product"
    description: str = ("Use this tool when you need to filter products with certain conditions. "
                        "To use the tool, you need to pass a full sentence describe the requirement.")

    def _run(self, criteria):
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        retries = 0
        while retries < 2:
            try:
                # get the last round filter
                last_round_filter = workflow['workflow_memory'].filters
                # set last_round_filter to empty dict if it is None
                last_round_filter = {} if last_round_filter is None else last_round_filter

                # shopping list
                shopping_list = workflow['workflow_memory'].shopping_list

                # get the filtered_products
                last_round_products = workflow['workflow_memory'].filtered_products

                logging.info(f"* Input criteria: {criteria}")
                parsed_criteria = _parse_criteria(criteria)
                logging.info(f"* Parsed criteria: {criteria}")

                logging.info(f"* Start parsing criteria:")
                filter_update_status, sql_filter, rag_filter, filters = _update_filter_status(last_round_filter, parsed_criteria)
                logging.info(f"* -- Filter update status: {filter_update_status}")
                logging.info(f"* -- sql filter: {sql_filter}")
                logging.info(f"* -- rag filter: {rag_filter}")
                
                if last_round_products is None or last_round_products.empty or filter_update_status == "update":
                    # need to rerun the filters on all the products
                    last_round_products = workflow['workflow_memory'].all_available_products
                
                if shopping_list is not None and not shopping_list.empty:
                    last_round_products = last_round_products[~last_round_products['ITEM_ID'].isin(shopping_list['ITEM_ID'])]
                
                if 'QUANTITY_BREAK_PRICING' in last_round_products.columns:
                    last_round_products = last_round_products.drop(columns=['QUANTITY_BREAK_PRICING'])
                    
                # start filtering
                logging.info(f"* Start use sql filtering products:")
                filtered_products = _filter_by_sql(last_round_products, sql_filter)
                logging.info(f"* Finish filtering products:")

                # check sql filtering result
                if filtered_products is None or filtered_products.empty:
                    return self._on_failure_no_product_avaliable()
                logging.info(f"* Start use RAG filtering products:")
                
                # start RAG filtering
                filtered_products = _filter_by_RAG(filtered_products, rag_filter)
                logging.info(f"* Finish RAG filtering:")
                filtered_products = _verify_filtering_result(filtered_products, rag_filter)
                logging.info(f"* Finish Varify filtering result")

                if filtered_products is None or filtered_products.empty:
                    return self._on_failure_no_product_avaliable()
                
                retries = float('inf')
            except Exception as e:
                logging.error(f"Error on first try when doing Filter Product", exc_info=True)
                retries += 1
        
        if retries == 2:
            return self._on_failure("I apologize, but I'm unable to filter the products based on your criteria. Could you please provide more specific details.")
        elif retries == float('inf'):
            filtered_products = filtered_products.copy()
            filtered_products.sort_values(by='RANK', inplace=True)
            return self._on_success(filters, filtered_products)

    def _arun(self, criteria):
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, filters, filtered_products):
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        memory = workflow['workflow_memory']
        memory.filtered_products = filtered_products
        memory.filters = filters

        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully get the filtered products."

        logging.info(f"* Sucessfully get the filtered products.")
        return to_next.message
    
    def _on_failure_no_product_avaliable(self):
        return self._on_failure("Unfortunately, no products match the applied filter. I have reset your filters to the previous settings. Please try again with different criteria.")
    
    def _on_failure(self, message=None):
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"Failed to execute your filtering condition {message}, can you be specific." if not message else message
        
        logging.info(f"* Fail to get the filtered products.")
        return to_next.message


def _parse_criteria(criteria):
    criteria_parsing_prompt = textwrap.dedent("""\
        Please follow the instructions to process the input query. Parse the query and generate a JSON object where each key represents a column name and the corresponding value is the associated criteria string for that column. Include only the column names that are mentioned in the provided query.
        
        SQL Database Columns:
        * color, a string contains the color of the product
        * price, a float number
        * is_retail_brand, a boolean value
        * is_eco_friendly, a boolean value
        * is_proud_path, a boolean value
        * is_new, a boolean value
        * brand_name, a string contains the brand name
        * product_type, a string contains the type of the product, eg: coaster set, tote bag, pen, pencil, etc
        * material, a string contains the material of the product, eg: plastic, metal, cotton, etc
        * size, a string contains the size of the product, eg: 12 oz, xxl, etc
                
        Example Query and the Corresponding Output:
        Query: "I would like a coaster set that is eco friendly and in proud path and color is blue or red and the brand is Apple, and it should be under 20" 
        Output should in this format: {{{{"product_type": "coaster set", "is_eco_friendly": "true", "is_proud_path": "true", "color": "blue or red", "brand_name": "Apple", "price": "<=20"}}}}
        
        Please follow previous instructions and parse the input query provided down below. Return your response as a JSON object within a markdown code block. Include only the columns mentioned in the query down below. Do not made up any additional columns.  Do not include any explanation and any additional information.
        
        Query:
        {criteria}
        """)
    
    response = _to_prompt_bot(criteria_parsing_prompt.format(criteria=criteria), use_service=True)
    return parse_json_markdown(response)


def _update_filter_status(last_round_filter, criteria):
    filters = copy.deepcopy(last_round_filter)
    
    append_or_update = "append"
    for key, value in criteria.items():
        if value is None:
            value = 'none'
        
        if not isinstance(value, str):
            value = str(value)
       
        # none null, nan means nonthing
        value = value.strip().lower()
        if value in ["none", "null", "nan", None, ""]:
            continue
        
        # check if the key is in the last_round_filter
        if key in last_round_filter:
            append_or_update = "update"
        filters[key] = value
    
    # Extract filterable columns from secrets for easy reference
    sql_columns = st.secrets.ipr.product.sql_filterable_columns
    rag_columns = st.secrets.ipr.product.rag_filterable_columns

    # Create filtered dictionaries using dictionary comprehensions
    sql_filter = {key: value for key, value in filters.items() if key in sql_columns}
    rag_filter = {key: value for key, value in filters.items() if key in rag_columns}
                        
    return append_or_update, sql_filter, rag_filter, filters


def _filter_by_sql(products, filter):
    if not filter:
        return products
    
    criteria_str = ", and ".join([f"{value}" for value in filter.items()])

    criteria_to_sql_prompt = textwrap.dedent("""\
        I have a SQL database which have the following columns:
        * available_colors, a list of color string separated by comma
        * price, a float number
        * is_retail_brand, a boolean value
        * is_eco_friendly, a boolean value
        * is_proud_path, a boolean value
        * is_new, a boolean value

        Sample Input Query And Corresponding Output:
        "(price, <=20), and (is_eco_friendly, true)", Output: ```where (price <= 20) and (is_eco_friendly = true)```
        
        Please parse the given query and create a SQL 'where' clause that includes only the criteria from the query.
        Always start the 'where' clause with 'where'.
        Enclose each condition within parentheses. 
        Put the 'where' clause within a markdown code snippet block.
        Do not made up any additional conditions. 
        Do not include any additional information.
        
        The query is: {criteria}
        """)
        
    response = _to_prompt_bot(criteria_to_sql_prompt.format(criteria=criteria_str), use_service=True)
    # Extract the SQL markdown from the response
    sql_code_pattern = re.compile(r"```(sql)?(.*)```", re.DOTALL)
    sql_code_match = sql_code_pattern.search(response)
    if sql_code_match is None:
        raise ValueError("No valid SQL markdown found. Ensure it is enclosed in triple backticks and labeled as 'sql'.")
    where_clause = sql_code_match.group(2).strip()

    products = ps.sqldf(
        f"SELECT * FROM products {where_clause}",
        locals()
    )
    
    return products


def _filter_by_RAG(products, filter, k=50):    
    if not filter:
        return products
    
    products_dict = {row['ITEM_ID']: row for _, row in products.iterrows()}
    # build a criteria string
    criteria_str = ", and ".join([f"{value}" for value in filter.values()])
    
    embedded_docs = _embedding(products['DOC_STRING'].tolist())
    embedded_query = _embedding(f"I want {criteria_str}")

    # Retrieve the most similar document
    similarity_scores = cos_sim(embedded_docs, embedded_query).flatten().tolist()
    top_docs = sorted(zip(products['ITEM_ID'].tolist(), similarity_scores), key=lambda x: x[1], reverse=True)[:k]

    filtered_products = pd.DataFrame([products_dict[item_id] for (item_id, _) in top_docs]).drop_duplicates(subset='ITEM_ID')


    return filtered_products if filtered_products.shape[0] else pd.DataFrame(columns=products.columns).astype(products.dtypes)


def _verify_filtering_result(filtered_products, filter):
    if not filter:
        return filtered_products
    
    verifying_prompt = textwrap.dedent("""\
        As a sales expert, your task is to assess the compatibility of a product with specific user requirements. This typically involves considerations such as the product's type, material, size, and brand. Carefully review the provided product description and the user's stated criteria. It is crucial to note that a 'true' match indicates the product exactly meets the user's requirements. For instance, if the user requests a mug, only a mug would constitute a true match. Anything else must be identified as 'false'.
            
        Product: {product}
            
        User Requirements: {criteria}
            
        Return 'true' only if the product precisely matches the user's requirements. If it does not, return 'false'.
        Please provide your response in the form of 'true' or 'false', do not include any additional information.
        
        Your response:
        """)
    
    criteria_str = ", and ".join([f"{value}" for value in filter.values()])
    progress = None
    try:
        progress = st.progress(0.0, text="Finding Product ...")
    except Exception:
        pass
    verified = []
    for idx, (_, row) in enumerate(filtered_products.iterrows()):
        try:
            if progress is not None:
                progress.progress((idx+1)/len(filtered_products), text=f"Filtering Product ... - {row['ITEM_NAME']}")
            response = _to_prompt_bot(verifying_prompt.format(product=row['DOC_STRING'], criteria=criteria_str))

            if "true" in response.lower():
                verified.append(row)
        except Exception as e:
            logging.error(f"Error:", exc_info=True)
    
    # it possible that none of the product can pass the filter
    # then we must return a empty dataframe    
    return pd.DataFrame(verified) if verified else pd.DataFrame(columns=filtered_products.columns).astype(filtered_products.dtypes)



def _to_prompt_bot(instruction, use_service=False):
    """Use promptbot when session state is available (main thread); otherwise call LLM directly (worker thread)."""
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
        logging.warning("Direct LLM fallback in filter_product failed: %s", e)
        return ""


def _embedding(docs):
    embedding_model = get_embeddings()
    if isinstance(docs, list):
        return embedding_model.embed_documents(docs)
    if isinstance(docs, str):
        return embedding_model.embed_query(docs)
    raise ValueError("Invalid input type. Must be a list of strings or a single string.")


def cos_sim(a, b):
    """
    Computes the cosine similarity cos_sim(a[i], b[j]) for all i and j using NumPy.
    
    :param a: A 2D NumPy array
    :param b: A 2D NumPy array
    :return: A 2D NumPy array where element [i, j] is the cosine similarity between a[i] and b[j]
    """
    # Ensure a and b are numpy arrays
    a = np.atleast_2d(a)
    b = np.atleast_2d(b)
    
    # Normalize each vector in a and b to have unit norm
    a_norm = a / np.linalg.norm(a, axis=1, keepdims=True)
    b_norm = b / np.linalg.norm(b, axis=1, keepdims=True)
    
    # Compute the matrix of cosine similarities
    cos_similarity = np.dot(a_norm, b_norm.T)
    return cos_similarity