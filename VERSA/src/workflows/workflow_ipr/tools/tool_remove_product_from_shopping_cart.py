import logging
import re

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow


class RemoveProductFromShoppingCart(BaseTool):
    name: str = "remove_product"
    description: str = ("Use this tool when you need to remove a product from shopping cart. To use the tool, you must provide a valid product id.")
    
    def _run(self, product_id: str) -> str:
        try:
            logging.info(f"* Delete product from shopping list: {product_id}")
            workflow = get_workflow()
            if not workflow:
                return "Workflow context not available."
            shopping_list = workflow['workflow_memory'].shopping_list
            
            product_id = _find_product_id(product_id)
            
            if product_id is None:
                return self._on_failure(message="I could not identify a valid product id in your input. To remove a product, can you please provide a valid product id?")
            
            if shopping_list is None or shopping_list.empty:
                return self._on_failure(message="Your shopping list is empty. You cannot remove any product.")
            
            status, shopping_list = _remove_product(product_id, shopping_list)
            
            if status:
                return self._on_success(product_id, shopping_list)
            else:
                return self._on_failure(message=f"I cannot remove a product ID {product_id} that is not in your shopping list.")
        except Exception as e:
            logging.error(f"Error while removing a product id-{product_id}", exc_info=True)
            return self._on_error(product_id)

    def _arun(self, product_id: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, product_id, shopping_list) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        memory = workflow['workflow_memory']
        memory.shopping_list = shopping_list

        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully removed the product {product_id} from your shopping list."
        return to_next.message

    def _on_failure(self,  product_id: str, message=None) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"The input code {product_id} is invalid." if not message else message
        return to_next.message

    def _on_error(self, distributor_id: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while validating the distributor id: {distributor_id}"
        return to_next.message


# =============================================================================
# DATA HANDLING
# =============================================================================
def _find_product_id(product_id):
    pattern = r'\b\w{2}-\w{4}\b|\b\w{4}-\w{2}\b'
    
    match = re.search(pattern, product_id)
    
    if match:
        return match.group()
    else:
        return None


def _remove_product(product_id, shopping_list):
    original_shape = shopping_list.shape[0]
    shopping_list = shopping_list[shopping_list['ITEM_ID'].str.lower() != product_id.lower()]
    after_shape = shopping_list.shape[0]
    
    if original_shape == after_shape:
        return False, shopping_list
    else:
        return True, shopping_list
