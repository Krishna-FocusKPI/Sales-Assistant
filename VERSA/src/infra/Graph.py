import logging
from typing import Callable, Dict, List

import streamlit as st
from graphviz import Digraph

START = "__start__"
END = "__end__"
HUMAN_FEEDBACK = "__Human Feedback__"


class GraphError(Exception):
    def __init__(self, message):
        self.message = message
        super().__init__(self.message)

    def __str__(self):
        return f"{self.message}"


class Graph:
    def __init__(self, name) -> None:
        self.name = name
        self.nodes: Dict[str, Callable] = {}
        self.edges: Dict[str, str] = {}
        self.conditional_edges: Dict[str, Dict[str, str]] = {}

    @property
    def num_nodes(self) -> int:
        return len(self.nodes)
    
    def add_node(self, key: str, node: Callable) -> None:
        if key in self.nodes:
            raise ValueError(f"Node `{key}` already present.")
        self.nodes[key] = node

    def add_edge(self, start_key: str, end_key: str) -> None:
        self.edges[start_key] = end_key

    def set_conditional_entry_point(
        self,
        condition: Callable[[], str],
        mapping: Dict[str, str]
    ):
        self.add_conditional_edges(START, condition, mapping)

    def add_conditional_edges(
        self,
        start_key: str,
        condition: Callable[[], str],
        mapping: Dict[str, str]
    ):
        if start_key not in self.nodes and start_key != START:
            raise ValueError(f"Node `{start_key}` is not defined.")
        self.conditional_edges[start_key] = (condition, mapping)

    def __call__(self) -> None:
        try:
            current_node = START
            while current_node != END and current_node != HUMAN_FEEDBACK:
                if current_node in self.conditional_edges:
                    condition, mapping = self.conditional_edges[current_node]
                    outcome = condition()
                    next_node = mapping.get(outcome)
                    if not next_node:
                        raise GraphError(f"No mapping for outcome `{outcome}` \
                            from node `{current_node}`")

                    # move statet to next node, so that we can skip for the next iteration
                    if next_node != END and next_node != HUMAN_FEEDBACK:
                        st.session_state.workflow['current_state'] = next_node

                    current_node = next_node
                elif current_node in self.edges:
                    current_node = self.edges[current_node]
                else:
                    raise GraphError(f"No path from node `{current_node}`")

                if current_node != END and current_node != HUMAN_FEEDBACK:
                    self.nodes[current_node]()
        except GraphError as e:
            logging.error(f"Error: {e}")
            raise e

    def set_entry_point(self, key: str) -> None:
        return self.add_edge(START, key)

    def set_finish_point(self, key: str) -> None:
        return self.add_edge(key, END)

    def plot_graph(self):
        g = Digraph('G')

        # Add nodes
        for node in self.nodes:
            g.node(node)

        # Add direct edges
        for start, end in self.edges.items():
            g.edge(start, end)

        # Handling conditional edges with labels
        for start_key, (condition, mapping) in self.conditional_edges.items():
            for outcome, target_key in mapping.items():
                g.edge(
                    start_key,
                    target_key,
                    label=f"{condition.__name__} -> {outcome}"
                )

        g.render(f"{st.secrets.dag.dag_dir}/{self.name}", format='png', view=False)
