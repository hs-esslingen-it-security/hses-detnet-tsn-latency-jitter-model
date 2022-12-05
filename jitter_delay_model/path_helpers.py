from typing import List

def get_ancestor_forwarding_node_name(path: List[str], node_index: int = None, node_name: str = None) -> str:
    """Returns the name of the forwarding node that comes before the given forwarding node (or one of its ports) in the forwarding path
    The given node is identified using the given node index or the given node name
    (only one of them is required).
    Returns None if there is no ancestor.
    """
    if node_name is None:
        node_name = path[node_index]

    # Get the forwarding node that belongs to the given port (if node isn't already a forwarding node)
    if '-' in node_name:
        forwarding_node_name = node_name.split('-')[0]
    else:
        forwarding_node_name = node_name

    forwarding_node_index = path.index(forwarding_node_name)

    if forwarding_node_index < 3:
        return None
    
    return path[forwarding_node_index - 3]

def get_ancestor_tx_port_node_name(path: List[str], node_index: int = None, node_name: str = None) -> str:
    """Returns the name of the tx port node that comes before the given forwarding node or port in the forwarding path
    The given node is identified using the given node index or the given node name
    (only one of them is required).
    Returns None if there is no ancestor.
    """
    if node_name is None:
        node_name = path[node_index]

    # Get the forwarding node that belongs to the given port (if node isn't already a forwarding node)
    if '-' in node_name:
        forwarding_node_name = node_name.split('-')[0]
    else:
        forwarding_node_name = node_name

    forwarding_node_index = path.index(forwarding_node_name)

    if forwarding_node_index < 2:
        return None
    
    return path[forwarding_node_index - 2]

def is_forwarding_node(node_name: str) -> bool:
    """Returns True if the given graph node name represents a forwarding node"""
    return '-' not in node_name

def is_port(node_name) -> bool:
    """Returns True if the given graph node name represents a port node"""
    return '-' in node_name

def is_rx_port(node_name: str, port_name: str, path: List[str]) -> bool:
    """Returns whether the given port is a receiving port on the given path, i.e., receives packets of the stream with the given path.
    
    If `node_name` and `port_name` are concatenated using "-" in one string, set `port_name` to None and only use `node_name`.
    """
    if port_name is not None:
        port_index = path.index(f'{node_name}-{port_name}')
    else:
        port_index = path.index(node_name)

    if port_index == 0:
        return False

    return '-' in path[port_index - 1] and '-' in path[port_index]

def is_tx_port(node_name: str, port_name: str, path: List[str]) -> bool:
    """Returns whether the given port is a sending port on the given path, i.e., sends packets of the stream with the given path.
    
    If `node_name` and `port_name` are concatenated using "-" in one string, set `port_name` to None and only use `node_name`.
    """

    if port_name is not None:
        port_index = path.index(f'{node_name}-{port_name}')
    else:
        port_index = path.index(node_name)

    if port_index == len(path) - 1:
        return False

    return '-' in path[port_index] and '-' in path[port_index + 1]
