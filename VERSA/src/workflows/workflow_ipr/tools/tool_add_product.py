import textwrap
import logging
import re

import pandas as pd
import streamlit as st
try:
    from langchain_core.tools import BaseTool
    from langchain_core.messages import HumanMessage
except ImportError:
    from langchain.tools import BaseTool
    from langchain_core.messages import HumanMessage

from src.common.provider import get_chat_model, get_default_provider
from src.common.workflow_context import get_workflow


class AddProduct(BaseTool):
    name: str = "add_product"
    description: str = ("Use this tool when the user said to add something. Input to this tool should be a string that describes the 'action', 'value', seperated by comma."
                        "The action should be one of the following: 'add_by_id', 'add_by_index', 'add_top', 'add_all', 'none'. Give 'none' if you can find a match action."
                        "Example Intput: 'add_by_id, 1234-56, 1234-57', 'add_by_index, 5', 'add_top, 4', 'add_all', 'none, tumbler'")

    def _run(self, criteria: str) -> str:
        if criteria.startswith("none"):
            return self._on_failure()
        
        # try input directly
        try: 
            logging.info(f"First try with criteria: {criteria}")
            parsed = [ele.strip() for ele in criteria.split(',')]
            
            action, value = parsed[0], ", ".join(f'"{item}"' for item in parsed[1:])
            
            if action == 'add_by_id':
                adding_status, updated_shopping_cart, message = _add_products_by_id(f"{value}", parsed=True)
            elif action == 'add_by_index':
                adding_status, updated_shopping_cart, message = _add_product_by_index(f"{value}", parsed=True)
            elif action == 'add_top':
                adding_status, updated_shopping_cart, message = _add_top_products(f"{value}", parsed=True)
            elif action == 'add_all':
                adding_status, updated_shopping_cart, message = _add_all_products()
            else:
                raise ValueError("Error parsing criteria by agent")
            
            if adding_status:
                return self._on_success(updated_shopping_cart, message)
            else:
                raise ValueError(f"Error on first try when doing Filter Product with {criteria}")
        except Exception as e:
            logging.error(f"Error on first try when doing Filter Product with {criteria}", exc_info=True)
        
        # try with prompt bot
        try:
            if not criteria.startswith("add "):
                criteria = "add " + criteria
            
            function_name = _identify_funtion_to_call(criteria)
            logging.info(f"Function name identified: {function_name}")
            
            if function_name == 'add_top_product':
                adding_status, updated_shopping_cart, message = _add_top_products(criteria)
            elif function_name == 'add_products_by_id':
                adding_status, updated_shopping_cart, message = _add_products_by_id(criteria)
            elif function_name == 'add_all':
                adding_status, updated_shopping_cart, message = _add_all_products()
            elif function_name == 'add_product_by_index':
                adding_status, updated_shopping_cart, message = _add_product_by_index(criteria)
            else:
                raise ValueError(f"Unknown function name: {function_name}")
                        
            if adding_status:
                return self._on_success(updated_shopping_cart, message)
            else:
                return self._on_failure(message)
        except Exception as e:
            logging.error(f"Error on first try when doing Filter Product", exc_info=True)
            return self._on_failure()

    def _arun(self, product_id: int):
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, updated_shopping_cart, message):
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        memory = workflow['workflow_memory']
        memory.shopping_list = updated_shopping_cart

        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = message

        logging.info(f"* {message}")
        return to_next.message
    
    def _on_failure_could_not_find(self, message):
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = textwrap.dedent("""\
            It seems that you are trying to add a product, but I couldn't understand your request '{message}'. Can you rephrase it? I can help you with these adding methods:
            - Add top x products / add first x products
            - Add the first one
            - Add xxxx-xx, yyyy-yy
            """)
    
    def _on_failure(self, message=None):
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = textwrap.dedent("""\
            It seems that you are trying to add a product, but I couldn't understand your request '{message}'. Can you rephrase it? I can help you with these adding methods:
            - Add top x products / add first x products
            - Add the first one
            - Add xxxx-xx, yyyy-yy
            """) if not message else message
        
        logging.info(f"* can not add.")
        return "Failed to add product."


def _add_top_products(criteria: str, parsed=False): 
    if not parsed:
        instruction = textwrap.dedent(f"""\
            Please review the user's request to add the top 'x' number of products. Can you determine the 'x' value from their query?
            Your output should only include the number. Do not include any additional information and explainations in the output.
            Request: {criteria}
            """)
    
        response = _to_prompt_bot(instruction)
    else:   
        response = criteria

    match = re.search(r'\d+', response)

    if not match:
        return False, None, f"Could not identif your request \"{criteria}\", you can say add top 5."
    
    top_x = int(match.group())
    
    workflow = get_workflow()
    if not workflow:
        return False, None, "Workflow context not available."
    filtered_products = workflow['workflow_memory'].filtered_products
    all_available_products = workflow['workflow_memory'].all_available_products
    product_list = filtered_products if filtered_products is not None and not filtered_products.empty else all_available_products

    if top_x <= 0:
        return False, None, f"It seems that you want to add top \"{top_x}\" which is not valid, can specify a valid number."
    
    products_to_add = product_list.head(top_x)['ITEM_ID'].tolist()
    
    if products_to_add:
        return _add_products(products_to_add)
    else:
        return False, None, "I could not find any products to add. Please try again."
    

def _add_all_products():
    return False, None, "I wasn't able to add every product to your list as it may have been too extensive. How about we tackle it in smaller batches?"


def _add_product_by_index(criteria: str, parsed=False):
    if not parsed:
        instruction = textwrap.dedent(f"""\
            Please analyze the request provided by the user who want to add products by the the index number. Can you identify the index from the query?
            for exmaple, when user input "add first" - output should be 1.
            
            User Input:
            {criteria}
            
            Your output should only include the index based on the provided user input. Do not include any additional information and explainations in the output.
            """)
        
        response = _to_prompt_bot(instruction)
        logging.info(f"Response: {response}")
    else:
        response = criteria
    
    match = re.search(r'\d+', response)

    if not match:
        return False, None, "It seems you want to add a product by its position, but I couldn't determine which product position you meant. Typically, you might say something like 'I want the first product.' Could you please specify the position again?"
    
    index = int(match.group())

    workflow = get_workflow()
    if not workflow:
        return False, None, "Workflow context not available."
    filtered_products = workflow['workflow_memory'].filtered_products
    all_available_products = workflow['workflow_memory'].all_available_products
    product_list = filtered_products if filtered_products is not None and not filtered_products.empty else all_available_products
        
    if 0 < index <= product_list.shape[0]:
        item_id = product_list.iloc[index-1]['ITEM_ID']
        return _add_products([item_id])
    else:
        return False, None, " it seems you want to add a product by its position, but I couldn't determine which product position you meant. Typically, you might say something like 'I want the first product.' Could you please specify the position again?"
    

def _add_products_by_id(criteria, parsed=False):
    if not parsed:
        instruction = textwrap.dedent(f"""\
        Please analyze the request provided by the user who want to add products id to shopping cart. Can you identify the product IDs from the query?
        
        Product ID Formating;
         The product_id typically follows the format xxxx-xx or xx-xxxx.
    
        Examplle:
        "add 1234-56". output: ```["1234-56"]```
        "add SM-1234 and 1234-56". output: ```["SM-1234", "1234-56"]```
        "add 1234-56, 1234-57". output: ```["1234-56", "1234-57"]```
        
        Please put the json array in a markdown code snippet block. Do not include any additional information and explainations in the output.
        Request:
        {criteria}
        """)
    
        response = _to_prompt_bot(instruction)
    else:
        response = criteria
        
    items = re.findall(r'["\']([a-zA-Z0-9\-]+)["\']', response)
    
    return _add_products(items)
    

def _add_products(product_ids: list):
    workflow = get_workflow()
    if not workflow:
        return False, None, "Workflow context not available."
    all_available_products = workflow['workflow_memory'].all_available_products
    shopping_cart = workflow['workflow_memory'].shopping_list
    
    # find products to add ignore case
    products_to_add = all_available_products[all_available_products['ITEM_ID'].str.upper().isin([x.upper() for x in product_ids])]
    
    # if no products match the ids
    if products_to_add.empty:
        return False, None, "Sorry, I couldn't find any products with the given IDs. Please try again."

    if shopping_cart is None or (hasattr(shopping_cart, 'empty') and shopping_cart.empty):
        updated_shopping_cart = products_to_add.copy()
    else:
        updated_shopping_cart = pd.concat([shopping_cart, products_to_add])
    updated_shopping_cart = updated_shopping_cart.drop_duplicates(subset='ITEM_ID')
    
    items_str = ', '.join(products_to_add['ITEM_ID'].astype(str).tolist())
    
    if products_to_add['FROM_SLUGGER'].any():
        slugger_items = products_to_add[products_to_add['FROM_SLUGGER'] == True]
        mem = workflow['workflow_memory']
        logo_or_company = getattr(mem, 'logo_name', None) or getattr(mem, 'industry', 'the company')
        if slugger_items.shape[0] == 1:
            slugger_items = ', '.join(slugger_items['ITEM_ID'].astype(str).tolist())

            message = (
                f"Successfully added this products: {items_str}. "
                f"Please note that {items_str} is not in the recommendation list, "
                f"which means {logo_or_company} may have already purchased it in the past 6 months."
            )
        else:
            slugger_items = ', '.join(slugger_items['ITEM_ID'].astype(str).tolist())

            message = (
                f"Successfully added these products: {items_str}. "
                f"Please note that these products {items_str} are not in the recommendation list, "
                f"which means {logo_or_company} may have already purchased them in the past 6 months."
            )
        return True, updated_shopping_cart, message
    else:
        if products_to_add.shape[0] == 1:
            return True, updated_shopping_cart, f"Successfully added this product: {items_str}."
        else:
            return True, updated_shopping_cart, f"Successfully added these products: {items_str}."


def _identify_funtion_to_call(criteria: str):
    instruction = textwrap.dedent(f"""\
        Please analyze the criteria provided by the user to determine which function should be called to add products.
        The product_id typically follows the format xxxx-xx or xx-xxxx. If the user give a bad input which does not fall into any options, please return 'none'.
        
        Function Options:
        add_top_product: Call this function when the user wishes to add the top 'x' products or the first 'x' products.
        add_products_by_id: Use this when the user supplies one or more specific product IDs. Product IDs are typically in the format xxxx-xx or xx-xxxx.
        add_all: Use this to add all products.
        add_product_by_index: Use this when the user provides a numerical index for the product. for example "add first", "add second".
        none: Use this when the user's request does not match any of the above functions.
        
        Criteria:
        {criteria}

        Please only output only one function name. Do not include any additional information in your response. Do not include your explainations in the output.        
        """)
    
    response = _to_prompt_bot(instruction)

    if "Functoin Name:" in response:
        response = response.replace("Functoin Name:", "").strip()
    elif "Function Name" in response:
        response = response.replace("Function Name", "").strip()
    else: 
        response = response.strip()
        
    return response
    

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
        logging.warning("Direct LLM fallback in add_product failed: %s", e)
        return ""
