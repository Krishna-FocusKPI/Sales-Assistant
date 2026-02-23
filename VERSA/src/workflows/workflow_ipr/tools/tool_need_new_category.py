import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow


class NeedNewCategory(BaseTool):
    name: str = "new_category"
    description: str = ("Use this tool when you need to go with a new category. "
                        "To use the tool, you need to pass 'true' you want to keep exploring another category")

    def _run(self, decision: str) -> str:
        try:
            if decision.strip() == 'true':
                return self._on_success()
            else:
                return self._on_failure(decision)
        except Exception as e:
            logging.error(f"Error while validating user choice {decision}", exc_info=True)
            return self._on_error()

    def _arun(self, category_name: int):
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully varified your choice."
        return to_next.message

    def _on_failure(self, decision: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"Fail to varify the choice {decision}."
        return to_next.message

    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while validating user choice."
        return to_next.message
