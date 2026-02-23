import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow

class EndProcess(BaseTool):
    name: str = "end_prcocess"
    description: str = ("Use this tool when you want to end."
                        "To use the tool, you must provide a boolean string."
                        "Give 'true' when the user want to end"
                        "or 'false' when the user want to continue the conversation.")

    def _run(self, decision: str) -> str:
        try:
            logging.info(f"* End process.")                
            return self._on_success() if decision.lower() == 'true' or decision == True else self._on_failure()
        except Exception as e:
            logging.error(f"Error while ending the process:", exc_info=True)
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
        to_next.message = "Sucessfully ended the process."
        return to_next.message
    
    def _on_failure(self, decision=None) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        
        to_next.message = "The user do not want to end the process."
        return to_next.message
    
    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        
        to_next.message = "Error while ending the process."
        return to_next.message