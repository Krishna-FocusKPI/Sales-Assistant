import base64
import textwrap

import streamlit as st
try:
    from langchain_core.prompts import ChatPromptTemplate
except ModuleNotFoundError:
    from langchain.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

from src.common.provider import get_chat_model, get_default_provider
from src.infra.Node import Node


class ToHumanNode(Node):
    def __init__(self, name="To Human", provider: str | None = None) -> None:
        super().__init__(name)
        _provider = provider or get_default_provider()
        self.agent = get_chat_model(_provider, temperature=0, max_tokens=2000)

    @property
    def rewrite_template(self):
        template = textwrap.dedent("""Please rewrite the following message. Do not add any additional information. Do not say anything that your response is an rewritten message. Do not wrap the message in quotes.

        Message to be rewritten:
        {message}

        Rewritten Message:
        """)
        return ChatPromptTemplate.from_template(template)
    
    @property
    def chunk_size(self):
        return 20

    def rewrite(self, message):
        prompt = self.rewrite_template.format_prompt(message=message)

        # streaming response
        full_response = ""
        with st.chat_message("AI"):
            placeholder = st.empty()

            for chunk in self.agent.stream(prompt):
                full_response += chunk.content
                placeholder.markdown(full_response)
            placeholder.markdown(full_response)

        st.session_state.messages.append(
            {
                "role": 'AI',
                "content": full_response
            }
        )
        return full_response
    
    def passthrough(self, message):
        chunks = [message[i:i + self.chunk_size]
                  for i in range(0, len(message), self.chunk_size)]

        # streaming response
        full_response = ""
        with st.chat_message("AI"):
            placeholder = st.empty()

            for chunk in chunks:
                full_response += chunk
                placeholder.markdown(full_response)
            placeholder.markdown(full_response)

        st.session_state.messages.append(
            {
                "role": 'AI',
                "content": full_response
            }
        )
        return full_response


    def __call__(self):
        to_next = st.session_state.workflow['to_next_memory']
       
        # check if message is provided
        if  (message := to_next.message) is None:
            raise ValueError("Message is required")

        # check if action is provided
        if (action := to_next.decision) is None:
            raise ValueError("Action is required")

        
        # check if action is valid
        if action == "rewrite":
            self.rewrite(message)
        elif action == "passthrough":
            self.passthrough(message)
        else:
            raise ValueError(f"Unknown message `{action}`")

        # reset the memory
        to_next.reset()
