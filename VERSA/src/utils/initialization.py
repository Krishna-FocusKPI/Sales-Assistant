import logging
import sys
import streamlit as st

from src.utils.deck_ttl_cleanup import cleanup_expired_generated_decks
from src.workflows.workflow_ipr.cache import cache_naics_code
from src.workflows.workflow_ipr.cache import cache_product as cache_ipr_product
from src.workflows.workflow_ppr.cache import cache_distributor as cache_ppr_distributor
from src.workflows.workflow_ppr.cache import cache_logo as chache_ppr_logo
from src.workflows.workflow_ppr.cache import cache_product as cache_ppr_product
from src.workflows.workflow_mpr.cache import cache_distributor as cache_mpr_distributor
from src.workflows.workflow_mpr.cache import cache_product as cache_mpr_product
from src.workflows.workflow_cbt.legacy_graph import (
    init_promptbot_graph,
    init_promptbot_service_graph,
    init_tohuman_graph,
)
class _SuppressScriptRunContextFilter(logging.Filter):
    """Drop Streamlit 'missing ScriptRunContext' warnings when running in worker threads (bare mode)."""

    def filter(self, record: logging.LogRecord) -> bool:
        msg = (record.getMessage() or "")
        if "ScriptRunContext" in msg and "bare mode" in msg:
            return False
        return True


@st.cache_resource
def setup_logger():
    logging.getLogger("httpx").setLevel(logging.CRITICAL)
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    if not any(isinstance(f, _SuppressScriptRunContextFilter) for f in root.filters):
        root.addFilter(_SuppressScriptRunContextFilter())
    # Ensure console output: root logger often has no handler when run via Streamlit
    if not root.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(logging.INFO)
        handler.setFormatter(logging.Formatter("%(asctime)s - %(message)s", datefmt="%m/%d/%Y %I:%M:%S %p"))
        root.addHandler(handler)

def init_in_session_workflow():    
    if "workflow" not in st.session_state:
        st.session_state.workflow = {}

def init_in_session_chatbot():
    # General chat uses LangGraph (run_chatbot_turn); no graph to init.
    if "tohuman" not in st.session_state:
        st.session_state.tohuman = init_tohuman_graph()
        
    if "promptbot" not in st.session_state:
        st.session_state.promptbot = init_promptbot_graph()
        
    if "promptbotservice" not in st.session_state:
        st.session_state.promptbotservice = init_promptbot_service_graph()


def init_in_session_chat_history():
    # init chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        st.session_state.messages.append(
            {
                "role": 'AI',
                "content": st.secrets.message.intro
            }
        )


def initialization():
    setup_logger()
    try:
        cleanup_expired_generated_decks()
    except Exception:
        logging.getLogger(__name__).debug("Deck TTL cleanup skipped", exc_info=True)

    # init session object
    init_in_session_chat_history()
    init_in_session_workflow()
    init_in_session_chatbot()
    
    # cache ppr
    chache_ppr_logo()
    cache_ppr_distributor()
    cache_ppr_product()
    
    # cache for ipr
    cache_ipr_product()
    cache_naics_code()

    # cache for mpr
    cache_mpr_distributor()
    cache_mpr_product()
