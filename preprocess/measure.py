from collections import defaultdict
import networkx as nx


def calculate_metrics(graph, name="Graph"):
    metrics = {}
    metrics["Nodes"] = graph.number_of_nodes()
    metrics["Edges"] = graph.number_of_edges()
    if graph.number_of_nodes() > 1:  # Avoid calculations for trivial graphs
        metrics["Density"] = nx.density(graph)
        metrics["Average Degree"] = sum(dict(graph.degree()).values()) / graph.number_of_nodes()
        metrics["Clustering Coefficient"] = nx.average_clustering(graph)
        try:
            metrics["Average Shortest Path Length"] = nx.average_shortest_path_length(graph)
        except nx.NetworkXError as e:
            metrics["Average Shortest Path Length"] = f"Not computable: {str(e)}"
    else:
        metrics["Density"] = "Not computable: Graph has one or zero nodes."
        metrics["Average Degree"] = "Not computable: Graph has one or zero nodes."
        metrics["Clustering Coefficient"] = "Not computable: Graph has one or zero nodes."
        metrics["Average Shortest Path Length"] = "Not computable: Graph has one or zero nodes."

    # Print metrics
    print(f"\n{name} Metrics:")
    for metric, value in metrics.items():
        print(f"  {metric}: {value}")
    return metrics





def group_nodes_by_instance(graph: nx.Graph):
    """
    Group nodes into subgraphs based on their 'instance' attribute.

    Parameters
    ----------
    graph : networkx.Graph
        The input graph with node attributes.

    Returns
    -------
    dict
        A dictionary where keys are instance names and values are subgraphs.
    """
    instance_subgraphs = defaultdict(list)
    for node, data in graph.nodes(data=True):
        instance = data.get('instance', "unknown")
        instance_subgraphs[instance].append(node)
    
    # Create subgraphs directly using nx.subgraph
    return {instance: graph.subgraph(nodes).copy() for instance, nodes in instance_subgraphs.items()}


def group_edges_by_type(graph: nx.Graph):
    """
    Group edges into subgraphs based on their 'edge_type' attribute.

    Parameters
    ----------
    graph : networkx.Graph
        The input graph with edge attributes.

    Returns
    -------
    dict
        A dictionary where keys are edge types and values are subgraphs.
    """
    edge_type_subgraphs = defaultdict(list)
    for u, v, data in graph.edges(data=True):
        edge_type = data.get("edge_type", "unknown")
        edge_type_subgraphs[edge_type].append((u, v))
    
    # Create subgraphs with only edges of the given type
    return {edge_type: nx.edge_subgraph(graph, edges).copy() for edge_type, edges in edge_type_subgraphs.items()}


# Analyze subgraphs by grouping (e.g., instances or edge types)
def analyze_grouped_subgraphs(graph, group_type='instance'):
    if group_type == 'instance':
        groups = group_nodes_by_instance(graph)
    elif group_type == 'edge_type':
        groups = group_edges_by_type(graph)
    else:
        raise ValueError("Invalid group type. Must be 'instance' or 'edge_type'.")
    
    group_metrics = dict()
    for group, subgraph in groups.items():
        group_metrics[group] = calculate_metrics(subgraph, name=f"{group_type}: {group}")
    return group_metrics
    


def analyze_cross_instance_statistics(graph: nx.Graph):
    """
    Analyze cross-instance interactions and compute relevant statistics.

    Parameters
    ----------
    graph : networkx.Graph
        The input graph with node attributes.

    Returns
    -------
    dict
        A dictionary containing statistics such as the cross-instance edge ratio
        and the percentage of nodes involved in cross-instance interactions.
    """
    # Total edges in the graph
    total_edges = graph.number_of_edges()

    # Find cross-instance edges
    cross_instance_edges = [
        (u, v) for u, v in graph.edges()
        if graph.nodes[u].get("instance") != graph.nodes[v].get("instance")
    ]
    num_cross_instance_edges = len(cross_instance_edges)

    # Compute cross-instance edge ratio
    cross_instance_edge_ratio = num_cross_instance_edges / total_edges if total_edges > 0 else 0

    # Nodes involved in cross-instance interactions
    cross_instance_nodes = set(u for u, v in cross_instance_edges).union(
        v for u, v in cross_instance_edges
    )
    total_nodes = graph.number_of_nodes()
    node_interaction_percentage = (len(cross_instance_nodes) / total_nodes * 100) if total_nodes > 0 else 0

    # Return results as a dictionary
    return {
        "Total Edges": total_edges,
        "Cross-Instance Edges": num_cross_instance_edges,
        "Cross-Instance Edge Ratio": cross_instance_edge_ratio,
        "Nodes Involved in Cross-Instance Interactions": len(cross_instance_nodes),
        "Node Interaction Percentage": node_interaction_percentage,
    }