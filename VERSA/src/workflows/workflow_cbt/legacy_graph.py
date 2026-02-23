from src.infra.Graph import END, Graph
from .node_tohuman.node import ToHumanNode
from .node_promptbot.node import PromptbotServiceNode, PromptbotNode


def init_tohuman_graph():
    # crate the nodes
    TOHUMAN = ToHumanNode()

    # create the graph
    graph = Graph(name="Tohuman Graph")

    # add the nodes to the graph
    graph.add_node("TOHUMAN", TOHUMAN)

    # add the edges to the graph
    graph.add_edge("TOHUMAN", END)

    # set the entry point
    graph.set_entry_point("TOHUMAN")

    # plot the graph
    # graph.plot_graph()

    return graph


def init_promptbot_graph():
    # crate the nodes
    PROMPTBOT = PromptbotNode()

    # create the graph
    graph = Graph(name="Promptbot Graph")

    # add the nodes to the graph
    graph.add_node("PROMPTBOT", PROMPTBOT)

    # add the edges to the graph
    graph.add_edge("PROMPTBOT", END)

    # set the entry point
    graph.set_entry_point("PROMPTBOT")

    # plot the graph
    # graph.plot_graph()

    return graph


def init_promptbot_service_graph():
    # crate the nodes
    PROMPTBOT = PromptbotServiceNode()

    # create the graph
    graph = Graph(name="Promptbot Service Graph")

    # add the nodes to the graph
    graph.add_node("PROMPTBOT", PROMPTBOT)

    # add the edges to the graph
    graph.add_edge("PROMPTBOT", END)

    # set the entry point
    graph.set_entry_point("PROMPTBOT")

    # plot the graph
    # graph.plot_graph()

    return graph
