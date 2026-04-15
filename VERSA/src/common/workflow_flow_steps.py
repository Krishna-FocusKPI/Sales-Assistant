"""
Flow steps and current-step logic for PPR, MPR, and IPR.
Used by the common right sidebar to show workflow progress and flowchart.
"""
from src.workflows import WorkFlows

# -----------------------------------------------------------------------------
# PPR
# -----------------------------------------------------------------------------
PPR_FLOW_STEPS = [
    "Validate Distributor",
    "Validate Logo",
    "Product Recommendations",
    "Customize products list",
    "Logo sales analysis",
    "Build Deck",
]


def _ppr_current_index(workflow: dict) -> int:
    """Infer current step 0..len(PPR_FLOW_STEPS)-1 from workflow_memory."""
    try:
        memory = workflow.get("workflow_memory")
        if not memory:
            return 0
        if not getattr(memory, "distributor_id", None) and not getattr(memory, "distributor_name", None):
            return 0
        if not getattr(memory, "logo_name", None):
            return 1
        has_category = getattr(memory, "category", None) or getattr(memory, "category_recommendation", None)
        all_products = getattr(memory, "all_available_products", None)
        shopping = getattr(memory, "shopping_list", None)
        has_products = all_products is not None and not (hasattr(all_products, "empty") and all_products.empty)
        has_list = shopping is not None and not (hasattr(shopping, "empty") and shopping.empty)
        if not has_category or (not has_products and not has_list):
            return 2
        if getattr(memory, "deck_name", None):
            return 5
        # Stay on Product Recommendations until there is a non-empty shopping list (not only a recommended-products table).
        if not has_list:
            return 2
        analysis = getattr(memory, "logo_sales_analysis", None)
        has_analysis = analysis is not None and not (hasattr(analysis, "empty") and analysis.empty)
        # Stay on "Customize products list" until analyze_logo_sales has persisted results.
        # Do not highlight "Logo sales analysis" while the bot is only about to run the tool.
        if not has_analysis:
            return 3
        return 4
    except Exception:
        return 0


# -----------------------------------------------------------------------------
# MPR
# -----------------------------------------------------------------------------
MPR_FLOW_STEPS = [
    "Validate Distributor",
    "Validate Category",
    "Product Recommendations",
]


def _mpr_current_index(workflow: dict) -> int:
    """Infer current step 0..len(MPR_FLOW_STEPS)-1 from workflow_memory."""
    try:
        memory = workflow.get("workflow_memory")
        if not memory:
            return 0
        if not getattr(memory, "distributor_id", None) and not getattr(memory, "distributor_name", None):
            return 0
        if not getattr(memory, "category", None):
            return 1
        return 2
    except Exception:
        return 0


# -----------------------------------------------------------------------------
# IPR
# -----------------------------------------------------------------------------
IPR_FLOW_STEPS = [
    "Validate NAICS",
    "Validate Category",
    "Product Recommendations",
    "Customize products list",
    "Build Deck",
]


def _ipr_current_index(workflow: dict) -> int:
    """Infer current step 0..len(IPR_FLOW_STEPS)-1 from workflow_memory."""
    try:
        memory = workflow.get("workflow_memory")
        if not memory:
            return 0
        if not getattr(memory, "naics_code", None) and not getattr(memory, "industry", None):
            return 0
        if not getattr(memory, "category", None):
            return 1
        all_products = getattr(memory, "all_available_products", None)
        shopping = getattr(memory, "shopping_list", None)
        has_products = all_products is not None and not (hasattr(all_products, "empty") and all_products.empty)
        has_list = shopping is not None and not (hasattr(shopping, "empty") and shopping.empty)
        if not has_products and not has_list:
            return 2
        if getattr(memory, "deck_name", None):
            return 4
        # Like PPR: do not show "Customize products list" until there is a real shopping list.
        # Recommendations alone (dataframe but empty list) stay on Product Recommendations.
        if not has_list:
            return 2
        return 3
    except Exception:
        return 0


# -----------------------------------------------------------------------------
# API for right sidebar
# -----------------------------------------------------------------------------
def get_flow_steps(workflow_name: str) -> list[str]:
    """Return the list of step labels for the given workflow, or empty if unknown."""
    if workflow_name == WorkFlows.WORKFLOW_PPR.value:
        return PPR_FLOW_STEPS
    if workflow_name == WorkFlows.WORKFLOW_MPR.value:
        return MPR_FLOW_STEPS
    if workflow_name == WorkFlows.WORKFLOW_IPR.value:
        return IPR_FLOW_STEPS
    return []


def get_current_step_index(workflow: dict) -> int:
    """Infer current step index (0-based) from workflow memory. Returns 0 if unknown."""
    if not workflow:
        return 0
    name = workflow.get("name")
    if name == WorkFlows.WORKFLOW_PPR.value:
        return _ppr_current_index(workflow)
    if name == WorkFlows.WORKFLOW_MPR.value:
        return _mpr_current_index(workflow)
    if name == WorkFlows.WORKFLOW_IPR.value:
        return _ipr_current_index(workflow)
    return 0
