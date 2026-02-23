import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow


class ProceedOrNot(BaseTool):
    name: str = "proceed_or_not"
    description: str = ("Use this tool when user want to procced."
                        "To use the tool, you need to provide a boolean string,"
                        "'true' if the user affirm otherwise 'false'")

    def _run(self, decision: bool) -> str:
        try:
            if decision == 'true' or decision == True:
                return self._on_success()
            else:
                return self._on_failure()
        except Exception as e:
            logging.error(f"Error while making decision:", exc_info=True)
            return self._on_error()

    def _arun(self, distributor_id: str) -> str:
        raise NotImplementedError("This tool does not support async")

    def _on_success(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "User confirmed to proceed."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = "User confirmed to proceed."
        return to_next.message

    def _on_failure(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "User decided not to proceed."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = "User decided not to proceed."
        return to_next.message

    def _on_error(self) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error while making decision."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = "Error while making decision."
        return to_next.message
