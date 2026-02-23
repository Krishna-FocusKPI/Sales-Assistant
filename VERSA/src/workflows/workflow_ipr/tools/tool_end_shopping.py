import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow


class EndShopping(BaseTool):
    name: str = "end_shopping"
    description: str = ("Use this tool when you want to finish the shopping process or "
                        "they want to proceed and go to next step. "
                        "To use the tool, you must provide true of false that indicate end or not.")
    
    def _run(self, decision: str) -> str:
        try:
            logging.info(f"* End shopping.")
            
            # check decision
            if decision.lower() != 'true':
                self._on_failure()
            
            # check shopping cart is empty
            workflow = get_workflow()
            if not workflow:
                return "Workflow context not available."
            shopping_list = workflow['workflow_memory'].shopping_list
            if shopping_list is None or workflow['workflow_memory'].shopping_list.shape[0] == 0:
                return self._on_failure_empty_cart()
            
            return self._on_success()
        except Exception as e:
            logging.error(f"Error while ending the shopping process:", exc_info=True)
            return self._on_error()

    def _arun(self, distributor_id: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully ended the shopping process."
        return to_next.message

    def _on_failure_empty_cart(self) -> str:
        return self._on_failure("Hello! It seems like you did not select any product yet. "
                               "To proceed, you'll need to select some products first. "
                               "Please take a moment to browse through our items and add your choices to the cart. "
                               "You can find your current select in the side panel.")
    
    def _on_failure(self, decision=None) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        
        to_next.message = decision if decision else "The input for end the shopping process is invalid." 
        return to_next.message

    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while ending the shopping process."
        return to_next.message
