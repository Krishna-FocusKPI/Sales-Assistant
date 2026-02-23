import json
import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow
from ..cache import cache_distributor


class ValidateDistributor(BaseTool):
    name: str = "validate_distributor"
    description: str = ("Use this tool when you need to validate distributor id. To use the tool, you must provide a distributor id.")
    
    def _run(self, distributor_id: str) -> str:
        try:
            logging.info(f"* Validating distributor id: {distributor_id}")
            exists, distributor_name, distributor_used_name = _distributor_id_exist(distributor_id)
            return self._on_success(distributor_id, distributor_name, distributor_used_name) if exists else self._on_failure(distributor_id)
        except Exception as e:
            logging.error(f"Error while validating distributor id param-distributor_id-{distributor_id}", exc_info=True)
            return self._on_error(distributor_id)

    def _arun(self, distributor_id: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, distributor_id: str, distributor_name: str, distributor_used_name: list) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.distributor_id = distributor_id
        memory.distributor_name = distributor_name
        memory.distributor_used_name = distributor_used_name
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully validate the input code."
        return to_next.message

    def _on_failure(self,  distributor_id: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"The input code {distributor_id} is invalid."
        return to_next.message

    def _on_error(self, distributor_id: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return f"An error occurred while validating the distributor id: {distributor_id}"
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while validating the distributor id: {distributor_id}"
        return to_next.message


# =============================================================================
# DATA HANDLING
# =============================================================================
def _distributor_id_exist(distributor_id: str) -> str:
    # Load the DataFrame containing distributor id and industry names
    df = cache_distributor()
    
    # Attempt to find the distributor id in the DataFrame (normalize types for comparison)
    match = df[df['DISTRIBUTOR_ID'].astype(str) == str(distributor_id)]
    
    # Check if there are any rows in the filtered DataFrame
    if not match.empty:
        # Return the industry name associated with the distributor id
        return True, match['DISTRIBUTOR_NAME'].iloc[0], json.loads(match['DISTRIBUTOR_USED_NAME'].iloc[0])
    else:
        return False, None, None
