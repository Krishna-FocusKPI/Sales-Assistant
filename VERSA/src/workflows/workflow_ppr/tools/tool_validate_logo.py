import logging

try:
    from langchain_core.tools import BaseTool
except ImportError:
    from langchain.tools import BaseTool

from src.common.workflow_context import get_workflow
from ..cache import cache_logo


class ValidateLogo(BaseTool):
    name: str = "validate_logo"
    description: str = ("Use this tool when you need to validate logo name which usually a company name. To use the tool, you must provide a logo name string.")
    
    def _run(self, logo_name: str) -> str:
        try:
            logging.info(f"* Validating logo name: {logo_name}")
            if not logo_name:
                self._on_failure("logo_name")
                
            exists, valid_logo_name, has_recurring = _logo_name_exist(logo_name)
            
            if exists:
                return self._on_success(valid_logo_name, has_recurring)
            
            exists, similar_logo = _have_similar_logo(logo_name)
            
            return self._on_success_with_candidates(similar_logo) if exists else self._on_failure(logo_name)
        except Exception as e:
            logging.error(f"Error while validating logo name param-logo_name-{logo_name}", exc_info=True)
            return self._on_error(logo_name)

    def _arun(self, logo_name: str) -> str:
        raise NotImplementedError("This tool does not support async")
    
    def _on_success_with_candidates(self, similar_logo) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.logo_candidates = similar_logo
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "HAVE_CANDIDATES"
        to_next.source = self.name
        to_next.message = f"Successfully found some matching candidates."
        return to_next.message

    def _on_success(self, logo_name: str, has_recurring: bool) -> str:
        workflow = get_workflow()
        if not workflow:
            return "Error: workflow context not available."
        memory = workflow['workflow_memory']
        memory.logo_name = logo_name
        memory.has_recurring = has_recurring
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "SUCCESS"
        to_next.source = self.name
        to_next.message = f"Sucessfully validate the logo name."
        return to_next.message

    def _on_failure(self,  logo_name: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return f"Could not find a matching for input {logo_name}."
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "FAILED"
        to_next.source = self.name
        to_next.message = f"Could not find a matching for input {logo_name}."
        return to_next.message

    def _on_error(self, logo_name: str) -> str:
        workflow = get_workflow()
        if not workflow:
            return f"An error occurred while validating the logo name: {logo_name}"
        to_next = workflow['to_next_memory']
        to_next.reset()
        to_next.decision = "ERROR"
        to_next.source = self.name
        to_next.message = f"An error occurred while validating the logo name: {logo_name}"
        return to_next.message


# =============================================================================
# DATA HANDLING
# =============================================================================
def _logo_name_exist(logo_name: str):
    # Load the DataFrame containing logo name
    df = cache_logo()
    
    # Attempt to find the logo name in the DataFrame
    match = df[df['CLIENT_NAME'].str.lower() == logo_name.lower()]
    
    # Check if there are any rows in the filtered DataFrame
    if not match.empty:
        # Return the industry name associated with the logo name
        return True, match['CLIENT_NAME'].iloc[0], match['HAS_RECURRING_REVENUE'].iloc[0]
    
    match = df[df['CLIENT_NAME'].str.contains(logo_name, case=False)]
    
    if match.shape[0] == 1:
        return True, match['CLIENT_NAME'].iloc[0], match['HAS_RECURRING_REVENUE'].iloc[0]

    return False, None, None
    

def _have_similar_logo(logo_name: str):
    # Load the DataFrame containing logo name
    df = cache_logo()

    match = df[df['CLIENT_NAME'].str.contains(logo_name, case=False)]

    if match.shape[0] > 0:
        return True, match.sort_values(by='TRANSACTION_COUNT', ascending=False)
    else:
        return False, None
