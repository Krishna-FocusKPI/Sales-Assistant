import base64
import os
import textwrap
from typing import Dict, List

import streamlit as st
from langchain_openai import ChatOpenAI
try:
    from langchain_core.prompts import ChatPromptTemplate
except ModuleNotFoundError:
    from langchain.prompts import ChatPromptTemplate


class Node:
    def __init__(self, name: str, step=1) -> None:
        self.name = name
        self.step = step

    @property
    def example_usage(self):
        pass
    
    def __call__(self) -> None:
        print(f"Node called with node: {self.name}")
