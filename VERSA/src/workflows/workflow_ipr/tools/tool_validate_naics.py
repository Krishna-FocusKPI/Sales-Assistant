import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow

from ..cache import cache_naics_code


class ValidateNAICS(BaseTool):
    name: str = "validate_naics"
    description: str = ("Use this tool when you need to validate NAICS code. To use the tool, you must provide a NAICS string.")
    
    def _run(self, naics_code: str) -> str:
        try:
            logging.info(f"* Validating NAICS code: {naics_code}")
            exists, industry = naics_code_exist(naics_code)
            return self._on_success(naics_code, industry) if exists else self._on_failure(naics_code)
        except Exception as e:
            logging.error(f"Error while validating NAICS code param-naics-{naics_code}", exc_info=True)
            return self._on_error(naics_code)

    def _arun(self, naics_code: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success(self, naics_code: str, industry: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        memory = workflow['workflow_memory']
        memory.naics_code = naics_code
        memory.industry = industry

        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully validate the input code."
        return to_next.message

    def _on_failure(self,  naics_code: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"The input code {naics_code} is invalid."
        return to_next.message

    def _on_error(self, naics_code: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Workflow context not available."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while validating the NAICS code: {naics_code}"
        return to_next.message

# =============================================================================
# DATA HANDLING
# =============================================================================
def naics_code_exist(naics_code: str) -> str:
    # Load the DataFrame containing NAICS codes and industry names
    df = cache_naics_code()
    
    # Attempt to find the NAICS code in the DataFrame
    match = df[df['NAICS_CODE'] == naics_code]
    
    # Check if there are any rows in the filtered DataFrame
    if not match.empty:
        # Return the industry name associated with the NAICS code
        return True, match['INDUSTRY_NAME'].iloc[0]
    else:
        return False, None
