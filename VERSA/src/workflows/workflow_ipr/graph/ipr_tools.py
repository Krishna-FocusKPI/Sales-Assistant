"""
IPR workflow: wrap legacy tool logic as StructuredTools for LangGraph/LangChain.
Each tool has a Pydantic args_schema; the same list is used for model.bind_tools()
and ToolNode(tools). Requires workflow in config when run from LangGraph (worker thread).
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field


def _get_ipr_tool_classes():
    from src.workflows.workflow_ipr.tools import (
        AddProduct,
        BuildDeck,
        EndProcess,
        EndShopping,
        FilterProduct,
        NeedNewCategory,
        ProductRecommendation,
        ProceedOrNot,
        RemoveProductFromShoppingCart,
        ResetFilter,
        ValidateCategory,
        ValidateNAICS,
    )
    return {
        "validate_naics": ValidateNAICS,
        "validate_category": ValidateCategory,
        "product_recommendation": ProductRecommendation,
        "filter_product": FilterProduct,
        "reset_filter": ResetFilter,
        "add_product": AddProduct,
        "remove_product_from_shopping_cart": RemoveProductFromShoppingCart,
        "end_shopping": EndShopping,
        "need_new_category": NeedNewCategory,
        "build_deck": BuildDeck,
        "end_process": EndProcess,
        "proceed_or_not": ProceedOrNot,
    }


# -----------------------------------------------------------------------------
# Pydantic args_schema: one model per tool
# -----------------------------------------------------------------------------

class _NoArgs(BaseModel):
    """No arguments."""
    pass


class ValidateNAICSArgs(BaseModel):
    naics_code: str = Field(description="NAICS code (industry code) string to validate.")


class ValidateCategoryArgs(BaseModel):
    category: str = Field(description="Category name to validate (e.g. Apparel, Drinkware).")


class FilterProductArgs(BaseModel):
    criteria: str = Field(description="Full sentence describing the filter (e.g. 'blue items under $20').")


class ResetFilterArgs(BaseModel):
    reset_string: str = Field(description="Filter name to reset, or 'all', or 'none'.")


class AddProductArgs(BaseModel):
    criteria: str = Field(description="Action and values, comma-separated: e.g. 'add_by_id, 1234-56', 'add_top, 5'.")


class RemoveProductArgs(BaseModel):
    product_id: str = Field(description="Product ID to remove from shopping cart.")


class EndShoppingArgs(BaseModel):
    decision: str = Field(description="Either 'true' or 'false'.")


class NeedNewCategoryArgs(BaseModel):
    decision: str = Field(description="Use 'true' to confirm new category.")


class EndProcessArgs(BaseModel):
    decision: str = Field(description="'true' to end, 'false' to continue.")


class ProceedOrNotArgs(BaseModel):
    decision: str = Field(description="'true' if user affirms, else 'false'.")


# Tool name -> (description, args_schema class)
_IPR_TOOL_SPECS: list[tuple[str, str, type[BaseModel]]] = [
    ("validate_naics", "Validate a NAICS (industry) code. Use when the user provides a NAICS code string. Returns whether the code exists and the industry name.", ValidateNAICSArgs),
    ("validate_category", "Validate a product category name. Use when the user selects or mentions a category.", ValidateCategoryArgs),
    ("product_recommendation", "Get product recommendations for the current industry (NAICS) and category. Uses workflow context; no parameters needed.", _NoArgs),
    ("filter_product", "Filter the current product list by criteria (e.g. color, price, brand). Pass a natural-language description of the filter.", FilterProductArgs),
    ("reset_filter", "Reset one or all filters. Pass a filter name or 'all' to reset all. Use 'none' only if no match.", ResetFilterArgs),
    ("add_product", "Add product(s) to the shopping cart. Actions: add_by_id, add_by_index, add_top, add_all, or none. Example: add_by_id, 1234-56, 1234-57.", AddProductArgs),
    ("remove_product_from_shopping_cart", "Remove a product from the shopping cart by product ID (e.g. 1234-56).", RemoveProductArgs),
    ("end_shopping", "Finish the shopping step and proceed. Pass 'true' to end shopping, 'false' otherwise.", EndShoppingArgs),
    ("need_new_category", "User wants to explore a new category. Pass 'true' to confirm.", NeedNewCategoryArgs),
    ("build_deck", "Build the recurring revenue PowerPoint deck from the current workflow state. No parameters needed.", _NoArgs),
    ("end_process", "End the entire process. Pass 'true' if the user wants to end, 'false' to continue.", EndProcessArgs),
    ("proceed_or_not", "Check if the user confirms to proceed. Pass 'true' for yes, 'false' for no.", ProceedOrNotArgs),
]


_AGENT_TOOL_LOG_PREFIX = "\033[94m"
_AGENT_TOOL_LOG_SUFFIX = "\033[0m"


def _execute_ipr_tool(name: str, args: dict[str, Any]) -> str:
    """Run the legacy IPR tool by name. Used by each StructuredTool's func."""
    logger.info("%sAgent calling tool: %s (args: %s)%s", _AGENT_TOOL_LOG_PREFIX, name, args, _AGENT_TOOL_LOG_SUFFIX)
    classes = _get_ipr_tool_classes()
    tool_class = classes.get(name)
    if not tool_class:
        return f"Unknown tool: {name}"
    instance = tool_class()
    result = instance.invoke(args)
    return result if isinstance(result, str) else str(result)


def _wrap_tool_with_workflow_context(tool):
    """Return a tool that sets workflow from config before invoke (for worker threads)."""
    from langchain_core.tools import StructuredTool
    from src.common.workflow_context import clear_workflow, set_workflow

    class _WorkflowContextTool(StructuredTool):
        def invoke(self, input, config=None, **kwargs):
            workflow = (config or {}).get("configurable", {}).get("workflow") if config else None
            if workflow is not None:
                set_workflow(workflow)
            try:
                return super().invoke(input, config=config, **kwargs)
            finally:
                if workflow is not None:
                    clear_workflow()

    return _WorkflowContextTool(
        name=tool.name,
        description=tool.description,
        func=tool.func,
        args_schema=tool.args_schema,
    )


def get_ipr_tools():
    """
    Return a list of StructuredTools for IPR. Use for model.bind_tools() and ToolNode(tools).
    Tools are wrapped so workflow from config is set in the current thread (for worker threads).
    """
    from langchain_core.tools import StructuredTool

    tools = []
    for name, description, args_schema in _IPR_TOOL_SPECS:
        def _make_func(tool_name: str):
            def _func(**kwargs: Any) -> str:
                return _execute_ipr_tool(tool_name, kwargs)
            return _func

        st = StructuredTool.from_function(
            func=_make_func(name),
            name=name,
            description=description,
            args_schema=args_schema,
        )
        tools.append(_wrap_tool_with_workflow_context(st))
    return tools


def execute_ipr_tool(name: str, args: dict[str, Any]) -> str:
    """Run the legacy IPR tool by name with the given args."""
    return _execute_ipr_tool(name, args)
