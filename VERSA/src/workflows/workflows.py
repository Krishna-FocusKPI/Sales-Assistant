import logging

import streamlit as st

from src.utils.logger import log

from . import WorkFlows
from .workflow_ipr.init_ipr_workflow import init_ipr_workflow
from .workflow_ppr.init_ppr_workflow import init_ppr_workflow
from .workflow_mpr.init_mpr_workflow import init_mpr_workflow


@log(log_info="STEP - ✓ Initialize workflow", log_level="STEP")
def init_workflow(user_input):
    def is_ipr():
        return "industry product recommendation" in user_input.lower() \
            or "ipr" in user_input.lower()
    
    def is_ppr():
        return "program product recommendation" in user_input.lower() \
            or "ppr" in user_input.lower()
            
    def is_mpr():
        return "market product recommendation" in user_input.lower() \
            or "mpr" in user_input.lower()
    
    # routering
    if is_ipr():
        logging.info("* Based on user input, initializing IPR workflow")
        init_ipr_workflow()
    elif is_ppr():
        logging.info("* Based on user input, initializing PPR workflow")
        init_ppr_workflow()
    elif is_mpr():
        logging.info("* Based on user input, initializing MPR workflow")
        init_mpr_workflow()
    else:
        logging.info("* User input not match any workflow")


@log(log_info="CHATBOT ACTION START", log_level="PROCESS", fill="░")
def routing(user_input, provider=None):
    logging.info(f"User Input: {user_input}")
    
    # if workflow is not set, then we run init workflow first
    if not st.session_state.workflow:
        init_workflow(user_input)

    # if workflow is set, run the workflow
    if st.session_state.workflow:
        if st.session_state.workflow.get("name") == WorkFlows.WORKFLOW_PPR.value:
            from src.workflows.workflow_ppr.graph import run_ppr_turn
            run_ppr_turn(user_input, provider=provider or "openai")
        elif st.session_state.workflow.get("name") == WorkFlows.WORKFLOW_MPR.value:
            from src.workflows.workflow_mpr.graph import run_mpr_turn
            run_mpr_turn(user_input, provider=provider or "openai")
        elif st.session_state.workflow.get("name") == WorkFlows.WORKFLOW_IPR.value:
            from src.workflows.workflow_ipr.graph import run_ipr_turn
            run_ipr_turn(user_input, provider=provider or "openai")
        else:
            graph = st.session_state.workflow["graph"]
            graph()
        # need to rerun the workflow to update the sidebar
        st.session_state.generation_in_progress = False
        st.rerun()
    else:
        from src.workflows.workflow_cbt.graph import run_chatbot_turn
        run_chatbot_turn(user_input, provider=provider or "openai")
        st.session_state.generation_in_progress = False
        st.rerun()
