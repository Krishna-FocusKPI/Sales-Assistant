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
            return "Successfully verified your choice. You can now pick a new category (e.g. recommend_category, then validate_category with the new name)."
        to_next = workflow.get("to_next_memory")
        if to_next:
            to_next.reset()
            to_next.decision = "SUCCESS"
            to_next.source = self.name
            to_next.message = "Successfully verified your choice."
        # Clear product state so "new category" gets fresh recommendations (same as legacy LoopSuccessDecision)
        memory = workflow.get("workflow_memory")
        if memory:
            memory.recommendations = None
            memory.all_available_products = None
            memory.filters = None
            memory.filtered_products = None
        return (to_next.message if to_next else "Successfully verified your choice. You can now choose a new category.")

    def _on_failure(self, decision: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return f"Fail to varify the choice {decision}."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"Fail to varify the choice {decision}."
        return to_next.message

    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "An error occurred while validating user choice."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while validating user choice."
        return to_next.message
