import textwrap

import streamlit as st
try:
    from langchain_core.prompts import ChatPromptTemplate
except ModuleNotFoundError:
    from langchain.prompts import ChatPromptTemplate

from src.common.provider import get_chat_model, get_default_provider
from src.infra.Node import Node


class PromptbotNode(Node):
    def __init__(self, name="Promptbot", provider: str | None = None) -> None:
        super().__init__(name)
        _provider = provider or get_default_provider()
        self.agent = get_chat_model(_provider, temperature=0, max_tokens=2000)
                
    def __call__(self):
        to_next = st.session_state.workflow['to_next_memory']
                
        # check if message is provided
        if  (message := to_next.message) is None:
            raise ValueError("Message is required")
        
        # check if action is provided
        if (action := to_next.action) is None:
            raise ValueError("Action is required")
        
        if action == "promptbot":
            template = ChatPromptTemplate.from_template(message)
            to_next.reset()
            
            to_next.source = "promptbot"
            to_next.action = "response"
            to_next.message = self.agent.invoke(input=template.format_prompt()).content
        else:
            raise ValueError(f"Unknown action: {action}")
        
        
class PromptbotServiceNode(Node):
    def __init__(self, name="Promptbot", provider: str | None = None) -> None:
        super().__init__(name)
        _provider = provider or get_default_provider()
        self.agent = get_chat_model(_provider, temperature=0)
                
    def __call__(self):
        to_next = st.session_state.workflow['to_next_memory']
                
        # check if message is provided
        if  (message := to_next.message) is None:
            raise ValueError("Message is required")
        
        # check if action is provided
        if (action := to_next.action) is None:
            raise ValueError("Action is required")
        
        if action == "promptbot":
            template = ChatPromptTemplate.from_template(message)
            to_next.reset()
            
            to_next.source = "promptbot"
            to_next.action = "response"
            to_next.message = self.agent.invoke(input=template.format_prompt()).content
        else:
            raise ValueError(f"Unknown action: {action}")