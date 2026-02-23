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
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool
from langchain_community.embeddings.ollama import OllamaEmbeddings

from src.common.workflow_context import get_workflow


class ResetFilter(BaseTool):
    name: str = "reset_filter"
    description: str = ("Use this tool when you want to reset. To use the tool, please provide a filter name. Please input 'all' if your want to reset all."
                        "The input filter name should be one of the following 'color', 'price', 'is_retail_brand', 'is_eco_friendly', 'is_proud_path', 'is_new', 'brand_name', 'product_type', 'material', 'size', 'none'."
                        "Give 'none' if you can find a match name.")
        
    def _run(self, reset_string: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        try:
            if reset_string == 'none':
                logging.info(f"* Could not identify the filter name.")
                return self._on_failure(reset_string)
            elif reset_string == "all":
                logging.info(f"* Resetting all filters")
                return self._on_success_reset_all(filters=None, filtered_products=None)
            else:
                logging.info(f"* Resetting filter: {reset_string}")
                name = reset_string

                # step 1: get filters
                filters = workflow['workflow_memory'].filters

                # step 2: check if the filter exists
                if not filters or name not in filters:
                    return self._on_failure(reset_string)

                # step 3: reset the filter
                filters = copy.deepcopy(filters)
                del filters[name]

                # step 4: get new filtered products
                all_available_products = workflow['workflow_memory'].all_available_products
                is_sucess, products = _update_filtered_products(filters, all_available_products)
                
                if is_sucess:
                    return self._on_success(filters, products)
                else:
                    # got an error while updating filtered products.
                    return self._on_success_reset_all(None, None)
        except Exception as e:
            logging.error(f"Error while reset filters {reset_string}", exc_info=True)
            return self._on_failure(reset_string)

    def _arun(self, reset_string: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success_reset_all(self, filters, filtered_products) -> str:
        message = "Sucessfully reset all filters."
        return self._on_success(filters, filtered_products, message)
    
    def _on_success(self, filters, filtered_products: str, message=None) -> str:
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
        to_next.message = "Sucessfully reset filters." if message is None else message
        return to_next.message

    def _on_failure(self, reset_string) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"The filter '{reset_string}' you want to reset is not currently applied." if reset_string != 'none' else "It appears that the filter you are trying to reset is not available. Could you please double-check?"
        return to_next.message

    def _on_error(self, reset_string: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while reset filter: {reset_string}"
        return to_next.message

# =============================================================================
# DATA HANDLING
# =============================================================================
def _update_filtered_products(filters, products):
    try:
        sql_columns = st.secrets.ipr.product.sql_filterable_columns
        rag_columns = st.secrets.ipr.product.rag_filterable_columns
        
        sql_filter = {key: value for key, value in filters.items() if key in sql_columns}
        rag_filter = {key: value for key, value in filters.items() if key in rag_columns}

        filtered_products = _filter_by_sql(products, sql_filter)
        
        if filtered_products is not None and not filtered_products.empty:
            filtered_products = _filter_by_RAG(filtered_products, rag_filter)
            filtered_products = _verify_filtering_result(filtered_products, rag_filter)
        return True, filtered_products
    except Exception as e:
        logging.error(f"Error while updating filtered products", exc_info=True)
        return False, None


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

        <Output Formatting>
        Please parse the given query and create a SQL 'where' clause that includes only the criteria from the query.
        Always start the 'where' clause with 'where'.
        Enclose each condition within parentheses. 
        Put the 'where' clause within a markdown code snippet block.
        Do not made up any additional conditions. 
        Do not include any additional information.
        Sample output ```where (price <= 20) and (is_eco_friendly = true)```

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

    return filtered_products


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
    
    verified = []
    for _, row in filtered_products.iterrows():
        try:
            response = _to_prompt_bot(verifying_prompt.format(product=row['DOC_STRING'], criteria=criteria_str))
            
            if "true" in response.lower():
                verified.append(row)
        except Exception as e:
            logging.error(f"Error:", exc_info=True)
    return pd.DataFrame(verified)


def _to_prompt_bot(instruction, use_service=False):
    workflow = get_workflow()
    if not workflow:
        return "Workflow context not available."
    to_next = workflow['to_next_memory']
    to_next.reset()
    to_next.message = instruction
    to_next.action = "promptbot"
    if use_service:
        st.session_state.promptbotservice()
    else:
        st.session_state.promptbot()
    return workflow['to_next_memory'].message


def _embedding(docs):
    embedding_model = OllamaEmbeddings(model=os.getenv('OPENAI_API_EMBEDDING_MODEL_NAME'), base_url=os.getenv('OPENAI_API_URL'))
    
    if type(docs) == list:
        return embedding_model.embed_documents(docs)
    elif type(docs) == str:
        return embedding_model.embed_query(docs)
    else:
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
