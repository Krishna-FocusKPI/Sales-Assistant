"""
PPR workflow: wrap legacy tool logic as StructuredTools for LangGraph/LangChain.
Each tool has a Pydantic args_schema; the same list is used for model.bind_tools()
and ToolNode(tools). Requires st.session_state.workflow when run in Streamlit.
"""
import logging
from typing import Any

logger = logging.getLogger(__name__)

from pydantic import BaseModel, Field

# Lazy import to avoid loading Streamlit and heavy workflow deps until tools are used.
def _get_ppr_tool_classes():
    from src.workflows.workflow_ppr.tools import (
        AddProduct,
        AnalyzeLogoSales,
        AnalyzeNews,
        AnalyzeYOY,
        BuildDeck,
        EndProcess,
        EndShopping,
        FilterProduct,
        NeedNewCategory,
        ProductRecommendation,
        ProceedOrNot,
        RecommendCategory,
        RemoveProductFromShoppingCart,
        ResetFilter,
        ValidateCategory,
        ValidateDistributor,
        ValidateLogo,
    )
    return {
        "validate_logo": ValidateLogo,
        "validate_distributor": ValidateDistributor,
        "recommend_category": RecommendCategory,
        "analyze_logo_sales": AnalyzeLogoSales,
        "analyze_yoy": AnalyzeYOY,
        "validate_category": ValidateCategory,
        "product_recommendation": ProductRecommendation,
        "filter_product": FilterProduct,
        "reset_filter": ResetFilter,
        "add_product": AddProduct,
        "remove_product": RemoveProductFromShoppingCart,
        "end_shopping": EndShopping,
        "new_category": NeedNewCategory,
        "build_deck": BuildDeck,
        "end_process": EndProcess,
        "analyze_news": AnalyzeNews,
        "proceed_or_not": ProceedOrNot,
    }


# -----------------------------------------------------------------------------
# Pydantic args_schema: one model per tool (ToolNode + bind_tools use these)
# -----------------------------------------------------------------------------

class _NoArgs(BaseModel):
    """No arguments."""
    pass


class ValidateLogoArgs(BaseModel):
    logo_name: str = Field(description="Company or logo name to validate.")


class ValidateDistributorArgs(BaseModel):
    distributor_id: str = Field(description="Distributor ID to validate.")


class ValidateCategoryArgs(BaseModel):
    category: str = Field(description="Category name to validate (e.g. Apparel, Drinkware).")


class FilterProductArgs(BaseModel):
    criteria: str = Field(description="Full sentence describing the filter (e.g. 'blue items under $20').")


class ResetFilterArgs(BaseModel):
    reset_string: str = Field(description="Filter name to reset, or 'all', or 'none'.")


class AddProductArgs(BaseModel):
    criteria: str = Field(description="Action and values, comma-separated: e.g. 'add_by_id, 1234-56', 'add_top, 5'.")


class RemoveProductArgs(BaseModel):
    product_id: str = Field(description="Product ID to remove.")


class EndShoppingArgs(BaseModel):
    decision: str = Field(description="Either 'true' or 'false'.")


class NewCategoryArgs(BaseModel):
    decision: str = Field(description="Use 'true' to confirm new category.")


class EndProcessArgs(BaseModel):
    decision: str = Field(description="'true' to end, 'false' to continue.")


class ProceedOrNotArgs(BaseModel):
    decision: str = Field(description="'true' if user affirms, else 'false'.")


# Tool name -> (description, args_schema class)
_PPR_TOOL_SPECS: list[tuple[str, str, type[BaseModel]]] = [
    ("validate_logo", "Validate a logo (company) name. Use when the user provides a company name to look up. Returns whether the logo exists and optional candidate matches.", ValidateLogoArgs),
    ("validate_distributor", "Validate a distributor ID. Use when the user provides a distributor code or ID.", ValidateDistributorArgs),
    ("recommend_category", "Recommend a product category for the current logo and distributor. Uses workflow context; no parameters needed.", _NoArgs),
    ("analyze_logo_sales", "Analyze logo vs distributor sales (YoY, share). Run after distributor and logo are validated and before build_deck; required for the deck's sales-analysis slide. Uses workflow context; no parameters needed.", _NoArgs),
    ("analyze_yoy", "Run year-over-year sales analysis for the current logo, distributor, and category. Uses workflow context; no parameters needed.", _NoArgs),
    ("validate_category", "Validate a product category name. Use when the user selects or mentions a category.", ValidateCategoryArgs),
    ("product_recommendation", "Get product recommendations for the current logo and category. Uses workflow context; no parameters needed.", _NoArgs),
    ("filter_product", "Filter the current product list by criteria (e.g. color, price, brand). Pass a natural-language description of the filter.", FilterProductArgs),
    ("reset_filter", "Reset one or all filters. Pass a filter name or 'all' to reset all. Valid names: color, price, is_retail_brand, is_eco_friendly, is_proud_path, is_new, brand_name, product_type, material, size. Use 'none' only if no match.", ResetFilterArgs),
    ("add_product", "Add product(s) to the shopping cart. Actions: add_by_id (product IDs like 1234-56), add_by_index (position number), add_top (top N), add_all, or none. Example: add_by_id, 1234-56, 1234-57.", AddProductArgs),
    ("remove_product", "Remove a product from the shopping cart by product ID (e.g. 1234-56 or xx-xxxx).", RemoveProductArgs),
    ("end_shopping", "Finish the shopping step and proceed. Pass 'true' to end shopping, 'false' otherwise.", EndShoppingArgs),
    ("new_category", "User wants to explore a new category. Pass 'true' to confirm.", NewCategoryArgs),
    ("build_deck", "Build the recurring revenue PowerPoint deck. Only call after analyze_logo_sales has completed successfully (build_deck will fail otherwise). No parameters needed.", _NoArgs),
    ("end_process", "End the entire process. Pass 'true' if the user wants to end, 'false' to continue.", EndProcessArgs),
    ("analyze_news", "Fetch and analyze news for the current logo. Uses workflow context; no parameters needed.", _NoArgs),
    ("proceed_or_not", "Check if the user confirms to proceed. Pass 'true' for yes, 'false' for no.", ProceedOrNotArgs),
]


# ANSI: light blue for console (94); reset (0)
_AGENT_TOOL_LOG_PREFIX = "\033[94m"
_AGENT_TOOL_LOG_SUFFIX = "\033[0m"


def _execute_ppr_tool(name: str, args: dict[str, Any]) -> str:
    """Run the legacy PPR tool by name. Used by each StructuredTool's func."""
    logger.info("%sAgent calling tool: %s (args: %s)%s", _AGENT_TOOL_LOG_PREFIX, name, args, _AGENT_TOOL_LOG_SUFFIX)
    classes = _get_ppr_tool_classes()
    tool_class = classes.get(name)
    if not tool_class:
        return f"Unknown tool: {name}"
    instance = tool_class()
    result = instance.invoke(args)
    return result if isinstance(result, str) else str(result)


def _wrap_tool_with_workflow_context(tool):
    """Return a tool subclass that sets workflow from config before invoke (for worker threads).
    StructuredTool is Pydantic so we can't monkey-patch; we create a new instance of a subclass.
    """
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


def get_ppr_tools():
    """
    Return a list of StructuredTools for PPR. Use this list for both:
    - model.bind_tools(tools)  (LLM gets schema from each tool's args_schema)
    - ToolNode(tools)         (LangGraph executes tool calls)
    One Pydantic model per tool = one args_schema per tool; the list is one tool per PPR action.
    Tools are wrapped so workflow from config is set in the current thread (for worker threads).
    """
    from langchain_core.tools import StructuredTool

    tools = []
    for name, description, args_schema in _PPR_TOOL_SPECS:
        def _make_func(tool_name: str):
            def _func(**kwargs: Any) -> str:
                return _execute_ppr_tool(tool_name, kwargs)
            return _func

        st = StructuredTool.from_function(
            func=_make_func(name),
            name=name,
            description=description,
            args_schema=args_schema,
        )
        tools.append(_wrap_tool_with_workflow_context(st))
    return tools


def execute_ppr_tool(name: str, args: dict[str, Any]) -> str:
    """
    Run the legacy PPR tool by name with the given args.
    Useful when you need to invoke a tool by name without going through ToolNode.
    """
    return _execute_ppr_tool(name, args)
