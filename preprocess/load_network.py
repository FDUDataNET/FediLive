import json
import networkx as nx
from pathlib import Path
import argparse

def load_replies_to_network(json_files, G:nx.DiGraph=None):
    """
    Load reply data from multiple JSON files into a NetworkX directed graph.

    Parameters
    -----------
    json_files : list of str
        List of file paths containing reply data in JSON format.
    G : nx.DiGraph, optional
        A directed graph where nodes represent users and edges represent replies.
        If not provided, a new directed graph is created. Default is None.

    Returns
    --------
    nx.DiGraph
        A directed graph where nodes represent users and edges represent replies.
    """
    if not G:
        G = nx.DiGraph()

    print("Loading *reply* interactions...")
    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for entry in data:
                # Extract the unique user IDs based on the 'url' field
                user_url = entry.get("acct", {}).get("url")
                reply_to_url = entry.get("reply_to_acct", {}).get("url")

                # Skip if required fields are missing
                if not user_url or not reply_to_url:
                    continue

                G.add_node(user_url)
                G.add_node(reply_to_url)

                # Add a directed edge from the replier to the user they replied to
                G.add_edge(user_url, reply_to_url, interaction="reply")

    return G


def load_boosters_favorites_to_network(json_files, G:nx.DiGraph=None):
    """
    Load booster and favorite data from multiple JSON files into a NetworkX directed graph.

    Parameters
    -----------
    json_files : list of str
        List of file paths containing booster and favorite data in JSON format.
    G : nx.DiGraph, optional
        A directed graph where nodes represent users and edges represent boosts or favorites.
        If not provided, a new directed graph is created. Default is None.

    Returns
    --------
    nx.DiGraph
        A directed graph where nodes represent users and edges represent boosts or favorites.
    """
    if not G:
        G = nx.DiGraph()

    print("Loading *booster* and *favourite* interactions...")
    for file_path in json_files:
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
            for entry in data:
                # Extract the account (post author) info
                post_author_url = entry.get("acct", {}).get("url")
                if not post_author_url:
                    continue

                # Add the post author as a node
                G.add_node(post_author_url, **entry.get("acct", {}))

                # Process boosters (reblogs)
                for booster in entry.get("reblogs", []):
                    if isinstance(booster, dict):  # Ensure booster is a dictionary
                        booster_url = booster.get("url")
                        if booster_url:
                            # G.add_node(booster_url, **booster)
                            G.add_node(booster_url)
                            G.add_edge(booster_url, post_author_url, interaction="boost")  # Add boost edge

                # Process favourites
                for favoriter in entry.get("favourites", []):
                    if isinstance(favoriter, dict):  # Ensure favoriter is a dictionary
                        favoriter_url = favoriter.get("url")
                        if favoriter_url:
                            G.add_node(favoriter_url)
                            G.add_edge(favoriter_url, post_author_url, interaction="favorite")  # Add favorite edge
    return G


def load_interaction_network(data_dir):
    """
    Load an interaction network from [FediLive](https://github.com/FDUDataNET/FediLive) crawled JSON files.

    Parameters
    -----------
    data_dir : str
        Directory containing JSON data files for replies, boosters, and favorites.

    Returns
    --------
    nx.DiGraph
        A directed graph representing interactions among users.
    """

    G = nx.DiGraph()

    # Get all booster/favorite and reply files
    data_path = Path(data_dir)
    booster_favorite_files = sorted(data_path.glob("boostersfavourites*.json"))
    reply_files = sorted(data_path.glob("reply*.json"))

    G = load_boosters_favorites_to_network(booster_favorite_files, G)
    G = load_replies_to_network(reply_files, G)

    return G

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Load interaction network from JSON files.")
    parser.add_argument("--data_dir", type=str, required=True, help="Directory containing JSON data files.")
    args = parser.parse_args()

    G = load_interaction_network(args.data_dir)
    print("Network loaded with {} nodes and {} edges".format(G.number_of_nodes(), G.number_of_edges()))