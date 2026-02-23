"""
MPR workflow: wrap tool implementations as StructuredTools for LangGraph.
Tools use get_workflow() so they work in worker threads when workflow is in config.
"""
import logging
from typing import Any

from pydantic import BaseModel, Field

logger = logging.getLogger(__name__)


def _get_mpr_tool_classes():
    from src.workflows.workflow_mpr.tools import (
        ProductRecommendation,
        ValidateCategory,
        ValidateDistributor,
    )
    return {
        "validate_distributor": ValidateDistributor,
        "validate_category": ValidateCategory,
        "product_recommendation": ProductRecommendation,
    }


class _NoArgs(BaseModel):
    pass


class ValidateDistributorArgs(BaseModel):
    distributor_id: str = Field(description="Distributor ID to validate.")


class ValidateCategoryArgs(BaseModel):
    category: str = Field(description="Category name to validate.")


_MPR_TOOL_SPECS: list[tuple[str, str, type[BaseModel]]] = [
    ("validate_distributor", "Validate a distributor ID. Use when the user provides a distributor code or ID.", ValidateDistributorArgs),
    ("validate_category", "Validate a product category name. Use when the user selects or mentions a category.", ValidateCategoryArgs),
    ("product_recommendation", "Get product recommendations for the current distributor and category. No parameters needed.", _NoArgs),
]

_AGENT_TOOL_LOG_PREFIX = "\033[94m"
_AGENT_TOOL_LOG_SUFFIX = "\033[0m"


def _execute_mpr_tool(name: str, args: dict[str, Any]) -> str:
    logger.info("%sAgent calling tool: %s (args: %s)%s", _AGENT_TOOL_LOG_PREFIX, name, args, _AGENT_TOOL_LOG_SUFFIX)
    classes = _get_mpr_tool_classes()
    tool_class = classes.get(name)
    if not tool_class:
        return f"Unknown tool: {name}"
    instance = tool_class()
    result = instance.invoke(args)
    return result if isinstance(result, str) else str(result)


def _wrap_tool_with_workflow_context(tool):
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


def get_mpr_tools():
    from langchain_core.tools import StructuredTool

    tools = []
    for name, description, args_schema in _MPR_TOOL_SPECS:
        def _make_func(tool_name: str):
            def _func(**kwargs: Any) -> str:
                return _execute_mpr_tool(tool_name, kwargs)
            return _func

        st = StructuredTool.from_function(
            func=_make_func(name),
            name=name,
            description=description,
            args_schema=args_schema,
        )
        tools.append(_wrap_tool_with_workflow_context(st))
    return tools
