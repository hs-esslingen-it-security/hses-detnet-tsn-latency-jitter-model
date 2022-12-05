from typing import Any, List, TypedDict, Union
import networkx as nx
import matplotlib.pyplot as plt

from latency_jitter_model.helpers import GclPriorities, ExpressPriorities, Priority, TopologyParsingError, debug, get_transmission_duration
from latency_jitter_model.path_helpers import is_forwarding_node, is_port
from latency_jitter_model.stream import Stream, StreamJson

TsnDomain = Union[str, None]

# All defaults are in nanoseconds or Mbit/s
DEFAULT_PROCESSING_DELAY = 1050
DEFAULT_PROCESSING_JITTER = 50
DEFAULT_SYNC_JITTER = 30
DEFAULT_TSN_DOMAIN = None

DEFAULT_GCL_ENABLED = False
DEFAULT_GCL_CYCLE = 1000000
DEFAULT_GCL_OPEN = 10000
DEFAULT_GCL_OFFSET = 1000

DEFAULT_LINK_SPEED = 1000
DEFAULT_MAX_FRAME_SIZE = 1522
DEFAULT_PROPAGATION_DELAY = 0
DEFAULT_TRANSMISSION_JITTER = 0
DEFAULT_FRAME_PREEMPTION_ENABLED = False
DEFAULT_EXPRESS_PRIORITIES = []
DEFAULT_GCL_PRIORITIES = [0, 1, 2, 3, 4, 5, 6, 7]

class PortAttrs(TypedDict):
    express_priorities: ExpressPriorities
    """Express priorities"""
    frame_preemption: bool
    """Whether frame preemption is enabled on the port"""
    gcl: bool
    """Whether a GCL is enabled on the port"""
    gcl_cycle: int
    """Cycle time of the GCL (ignored if GCL is disabled)"""
    gcl_open: int
    """Window of the GCL (ignored if GCL is disabled)"""
    gcl_offset: int
    """Offset if the window of the GCL (ignored if GCL is disabled)"""
    gcl_priorities: GclPriorities
    """Priorities of the GCL window (ignored if GCL is disabled)"""

class Port(PortAttrs):
    name: str
    """Name of the port"""

class NodeAttrs(TypedDict):
    processing_delay: int
    """Processing delay in ns"""
    processing_jitter: int
    """Processing jitter in ns"""
    sync_domain: str
    """
    Name of the TSN domain to which the node belongs to.
    Nodes in the same TSN domain must give an identical name.
    """
    sync_jitter: int
    """Time synchronization jitter in ns"""

class Node(NodeAttrs):
    name: str
    """Name of the node"""
    ports: List[Port]
    """Ports that belong to the node"""

class EdgeAttrs(TypedDict):
    link_speed: int
    """Link speed in Mbit/s on the edge"""
    max_frame_size: int
    """Maximum frame size on the edge in bytes"""
    propagation_delay: int
    """Propagation delay on the edge in ns"""
    transmission_jitter: int
    """Transmission jitter on the edge in ns"""

class Edge(EdgeAttrs):
    node1_name: str
    """Name of the first node the edge is connected to"""
    port1_name: str
    """Name of the port of the first node the edge is connected to"""
    node2_name: str
    """Name of the second node the edge is connected to"""
    port2_name: str
    """Name of the second of the first node the edge is connected to"""

class PortJson(TypedDict):
    name: str
    expressPriorities: ExpressPriorities
    framePreemption: bool
    """Whether frame preemption is enabled on the port"""
    gcl: bool
    gclCycle: int
    """GCL cycle in nanoseconds"""
    gclOpen: int
    """GCL open window in nanoseconds"""
    gclOffset: int
    """GCL offset in nanoseconds"""
    gclPriorities: GclPriorities
    """Priorities that are controlled by the gate"""

class NodeJson(TypedDict):
    name: str
    processingDelay: int
    """Processing delay in nanoseconds"""
    processingJitter: int
    """Processing jitter in nanoseconds"""
    syncDomain: str
    """Name of the domain to which the node belongs
    (if two nodes have the same domain name, they belong to the same domain)
    """
    syncJitter: int
    """Sync jitter in nanoseconds"""
    ports: List[PortJson]

class EdgeJson(TypedDict):
    port1: List[str]
    """Identifies the port marking the start of the edge.
    List that accepts two strings. 
    The first string is the node name.
    The second string is the port name.
    """
    port2: List[str]
    """Identifies the port marking the end of the edge.
    List that accepts two strings. 
    The first string is the node name.
    The second string is the port name.
    """
    linkSpeed: int
    """Link speed on the edge in Mbit/s"""
    maxFrameSize: int
    """Maximum transmittable frame size in bytes"""
    propagationDelay: int
    """Propagation delay in nanoseconds"""
    transmissionJitter: int
    """Transmission jitter in nanoseconds"""

class TopologyJson(TypedDict):
    name: str
    description: str
    """Optional"""
    nodes: List[NodeJson]
    edges: List[EdgeJson]
    streams: List[StreamJson]

class Topology:
    def __init__(self, name: str, description: str = ''):
        """
        @name: Name of the topology
        @description: Description of the topology (optional)
        """
        self.G = nx.Graph()
        self.streams: "list[Stream]" = []
        self.name = name
        """Name of the topology"""
        self.description = description
        """Optional description of the topology (empty string if no description is given)"""

    def add_node(self, name: str, processing_delay: int=DEFAULT_PROCESSING_DELAY, processing_jitter: int=DEFAULT_PROCESSING_JITTER, sync_domain: TsnDomain=DEFAULT_TSN_DOMAIN, sync_jitter: int=DEFAULT_SYNC_JITTER):
        self.G.add_node("{!s}".format(name), forwarding_node=True, processing_delay=processing_delay, processing_jitter=processing_jitter, sync_domain=sync_domain, sync_jitter=sync_jitter)

    def add_port_to_node(self,
        node_name: str, 
        port_name: str, 
        gcl=DEFAULT_GCL_ENABLED, 
        gcl_cycle=DEFAULT_GCL_CYCLE, 
        gcl_open=DEFAULT_GCL_OPEN, 
        gcl_offset=DEFAULT_GCL_OFFSET, 
        express_priorities: ExpressPriorities = DEFAULT_EXPRESS_PRIORITIES,
        gcl_priorities: GclPriorities = DEFAULT_GCL_PRIORITIES,
        frame_preemption: bool=DEFAULT_FRAME_PREEMPTION_ENABLED
    ):
        """
        @gcl_cycle: GCL cycle time
        @gcl_open: Point of time during a cycle when the gate opens
        @gcl_offset: Duration for which the gate is open
        """
        new_name = node_name + "-" + port_name
        self.G.add_node(
            "{!s}".format(new_name),
            forwarding_node=False,
            gcl=gcl,
            gcl_cycle=gcl_cycle,
            gcl_open=gcl_open,
            gcl_offset=gcl_offset,
            express_priorities=express_priorities,
            gcl_priorities=gcl_priorities,
            frame_preemption=frame_preemption
        )
        self.G.add_edge(node_name, new_name, internal=True)
        return new_name

    def add_edge(self, port_a: str, port_b: str, link_speed: int=DEFAULT_LINK_SPEED, propagation_delay: int=DEFAULT_PROPAGATION_DELAY, transmission_jitter: int=DEFAULT_TRANSMISSION_JITTER, max_frame_size: int=DEFAULT_MAX_FRAME_SIZE):
        self.G.add_edge(port_a, port_b, internal=False, link_speed=link_speed,
                        propagation_delay=propagation_delay, transmission_jitter=transmission_jitter, max_frame_size=max_frame_size)
        # self.G.add_edge(port_b, port_a.split("-")[0], internal=False, link_speed=link_speed,
        #                 propagation_delay=propagation_delay, transmission_jitter=transmission_jitter, max_frame_size=max_frame_size)

    def add_streams(self, streams: List[Stream]):
        self.streams.extend(streams)

    def get_forwarding_node_names(self) -> List[str]:
        """Returns the names of all forwarding nodes in the topology"""
        return [node_name for node_name in self.G.nodes if is_forwarding_node(node_name)]

    def get_port_names(self) -> List[str]:
        """Returns the names of all ports in the topology"""
        return [node_name for node_name in self.G.nodes if is_port(node_name)]

    def get_port_names_of_node(self, node_name: str) -> List[str]:
        """Returns the names of the ports that belong to the given node
        """
        return [port_name for port_name in self.G.nodes
            if is_port(port_name) and self.get_forwarding_node_name_by_port(port_name) == node_name]

    def get_forwarding_node_name_by_port(self, port_name: str) -> str:
        """Returns name of the forwarding node to which the given port belongs to
        """
        forwarding_node_name = port_name.split("-")[0]
        return forwarding_node_name

    def get_port_name_by_port(self, port_name: str) -> str:
        """Returns name of the port without the prepended forwarding node name
        """
        return port_name.split('-')[1]

    def are_synchronized(self, node1: str, node2: str) -> bool:
        """Returns whether the given nodes are synchronized (are in the same sync domain)

        @param node1 Name of the first node
        @param node2 Name of the second node
        """
        domain_1 = self.G.nodes(data=True)[node1]["sync_domain"]
        domain_2 = self.G.nodes(data=True)[node2]["sync_domain"]
        return domain_1 is not None and domain_2 is not None and domain_1 == domain_2
    
    def recalculate_gcl(self):
        """Updates the GCL window of each port based on the bandwidth of the streams
        TODO: deprecated?
        """
        all_ports = [node for node in self.G.nodes if "-" in node]

        for port in all_ports:
            streams = [stream for stream in self.streams if port in stream.path]
            total_bandwidth = sum([stream.get_bandwidth(port) for stream in streams]) + 20 * len(streams)
            # TODO: link speed is hardcoded here and should be fetched from corresponding edge instead
            window = get_transmission_duration(total_bandwidth, 1000)
            old_window = self.G.nodes(data=True)[port]["gcl_open"]
            self.G.nodes(data=True)[port]["gcl_open"] = max(old_window, window)
            debug(f"New window for port {port}: {max(old_window, window)}")

    def draw(self):
        # Differentiate between forwarding nodes and port nodes by giving them a different color
        node_color = ['red' if node['forwarding_node'] == True else 'blue' for i, node in self.G.nodes(data=True)]
        nx.draw(self.G, pos=nx.spring_layout(self.G), with_labels = True, node_color=node_color)
        plt.show()

    def to_json(self) -> TopologyJson:
        topology: TopologyJson = {}
        topology['name'] = self.name
        if self.description is not None or self.description != '':
            topology['description'] = self.description
        topology['nodes'] = []
        topology['edges'] = []
        topology['streams'] = []

        for node_name in self.get_forwarding_node_names():
            node_data: NodeAttrs = self.G.nodes(data=True)[node_name]
            node: NodeJson = {}
            node['name'] = node_name
            node['processingDelay'] = node_data['processing_delay']
            node['processingJitter'] = node_data['processing_jitter']
            node['syncDomain'] = node_data['sync_domain']
            if node_data['sync_domain'] == True or node_data['sync_jitter'] != DEFAULT_SYNC_JITTER:
                node['syncJitter'] = node_data['sync_jitter']
            node['ports'] = []

            for port_name in self.get_port_names_of_node(node_name):
                port_data: PortAttrs = self.G.nodes(data=True)[port_name]
                port: PortJson = {}
                port['name'] = port_name.replace(node_name + '-', '')
                port['framePreemption'] = port_data['frame_preemption']
                if port_data['frame_preemption'] == True or port_data['express_priorities'] != DEFAULT_EXPRESS_PRIORITIES:
                    port['expressPriorities'] = port_data['express_priorities']
                port['gcl'] = port_data['gcl']
                if port_data['gcl'] == True or port_data['gcl_cycle'] != DEFAULT_GCL_CYCLE:
                    port['gclCycle'] = port_data['gcl_cycle']
                if port_data['gcl'] == True or port_data['gcl_open'] != DEFAULT_GCL_OPEN:
                    port['gclOpen'] = port_data['gcl_open']
                if port_data['gcl'] == True or port_data['gcl_offset'] != DEFAULT_GCL_OFFSET:
                    port['gclOffset'] = port_data['gcl_offset']
                if port_data['gcl'] == True or port_data['gcl_priorities'] != DEFAULT_GCL_PRIORITIES:
                    port['gclPriorities'] = port_data['gcl_priorities']
                node['ports'].append(port)

            topology['nodes'].append(node)

        # Filter out all edges that are no connections between two ports
        edges = [edge for edge in self.G.edges() if is_port(edge[0]) and is_port(edge[1])]
        for edge_elem in edges:
            edge_data: EdgeAttrs = self.G.edges[edge_elem]
            edge: EdgeJson = {}
            edge["port1"] = [
                self.get_forwarding_node_name_by_port(edge_elem[0]),
                self.get_port_name_by_port(edge_elem[0])
            ]
            edge["port2"] = [
                self.get_forwarding_node_name_by_port(edge_elem[1]),
                self.get_port_name_by_port(edge_elem[1])
            ]
            edge['linkSpeed'] = edge_data['link_speed']
            edge['maxFrameSize'] = edge_data['max_frame_size']
            edge['propagationDelay'] = edge_data['propagation_delay']
            edge['transmissionJitter'] = edge_data['transmission_jitter']
            topology['edges'].append(edge)

        for stream in self.streams:
            topology['streams'].append(stream.to_json())

        return topology

    def edge_from_json(edge: dict) -> Edge:
        try:
            try:
                node_port_1 = edge['port1']
                node1 = str(node_port_1[0])
                port1 = str(node_port_1[1])
            except:
                raise TopologyParsingError('Invalid "port1" key in topology edge')

            try:
                node_port_2= edge['port2']
                node2 = str(node_port_2[0])
                port2 = str(node_port_2[1])
            except:
                raise TopologyParsingError('Invalid "port2" key in topology edge')

            link_speed = int(edge.get('linkSpeed', DEFAULT_LINK_SPEED))
            max_frame_size = int(edge.get('maxFrameSize', DEFAULT_MAX_FRAME_SIZE))
            propagation_delay = int(edge.get('propagationDelay', DEFAULT_PROPAGATION_DELAY))
            transmission_jitter = int(edge.get('transmissionJitter', DEFAULT_TRANSMISSION_JITTER))

        except TopologyParsingError:
            # We already "handled" this error
            raise
        except:
            # Unknown error
            raise TopologyParsingError(f'Error parsing edge between "{node1}-{port1}" and "{node2}-{port2}"')

        return {
            'node1_name': node1,
            'port1_name': port1,
            'node2_name': node2,
            'port2_name': port2,
            'link_speed': link_speed,
            'max_frame_size': max_frame_size,
            'propagation_delay': propagation_delay,
            'transmission_jitter': transmission_jitter
        }

    def _priority_list_from_json(raw_priorities: Any) -> List[Priority]:
        """
        Tries to convert any input to a list that follows the definition of a priority list. Raises in case of error.
        """
        priorities = []

        for value in raw_priorities:
            i = int(value)
            if i >= 0 and i <= 7:
                priorities.append(i)
            else:
                raise

        return priorities


    def port_from_json(port: dict, node_name: str) -> Port:
        try:
            if 'name' not in port:
                raise TopologyParsingError('Missing "name" key in port')
            name = str(port['name'])

            try:
                express_priorities = Topology._priority_list_from_json(port.get('expressPriorities', DEFAULT_EXPRESS_PRIORITIES))
            except:
                raise TopologyParsingError(f'"expressPriorities" key has wrong format in port {port} that belongs to node {node_name}')

            frame_preemption = bool(port.get('framePreemption', DEFAULT_FRAME_PREEMPTION_ENABLED))
            gcl = bool(port.get('gcl', DEFAULT_GCL_ENABLED))
            gcl_cycle = int(port.get('gcl_cycle', DEFAULT_GCL_CYCLE))
            gcl_open = int(port.get('gclOpen', DEFAULT_GCL_OPEN))
            gcl_offset = int(port.get('gclOffset', DEFAULT_GCL_OFFSET))
            
            try:
                gcl_priorities = Topology._priority_list_from_json(port.get('gclPriorities', DEFAULT_GCL_PRIORITIES))
            except:
                raise TopologyParsingError(f'"gclPriorities" key has wrong format in port {port} that belongs to node {node_name}')

        except TopologyParsingError:
            # We already "handled" this error
            raise
        except:
            # Unknown error
            raise TopologyParsingError(f'Error parsing port "{name}" that belongs to node {node_name}')

        return {
            'name': name,
            'express_priorities': express_priorities,
            'frame_preemption': frame_preemption,
            'gcl': gcl,
            'gcl_cycle': gcl_cycle,
            'gcl_open': gcl_open,
            'gcl_offset': gcl_offset,
            'gcl_priorities': gcl_priorities
        }

    def node_from_json(node: dict) -> Node:
        try:
            if 'name' not in node:
                raise TopologyParsingError('Missing "name" key in node')
            name = str(node['name'])

            processing_delay = int(node.get('processingDelay', DEFAULT_PROCESSING_DELAY))
            processing_jitter = int(node.get('processingJitter', DEFAULT_PROCESSING_JITTER))
            sync_domain = str(node.get('syncDomain', DEFAULT_TSN_DOMAIN))
            # Make sure we only use None (no empty string) if no sync domain is defined
            sync_domain = None if sync_domain == '' else sync_domain
            sync_jitter = int(node.get('syncJitter', DEFAULT_SYNC_JITTER))

            ports: List[Port] = []

            for port in node.get('ports', []):
                ports.append(Topology.port_from_json(port, name))


        except TopologyParsingError:
            # We already "handled" this error
            raise
        except:
            # Unknown error
            raise TopologyParsingError(f'Error parsing node "{name}"')

        return {
            'name': name,
            'processing_delay': processing_delay,
            'processing_jitter': processing_jitter,
            'sync_domain': sync_domain,
            'sync_jitter': sync_jitter,
            'ports': ports
        }

    def from_json(topology: dict) -> 'Topology':
        try:
            if 'name' not in topology:
                raise TopologyParsingError('Missing "name" key in topology')

            if 'nodes' not in topology or type(topology['nodes']) is not list:
                raise TopologyParsingError('Missing or invalid "nodes" key in topology')

            if 'edges' not in topology or type(topology['edges']) is not list:
                raise TopologyParsingError('Missing or invalid "edges" key in topology')

            if 'streams' not in topology or type(topology['streams']) is not list:
                raise TopologyParsingError('Missing or invalid "streams" key in topology')

            nodes = [Topology.node_from_json(node) for node in topology['nodes']]
            edges = [Topology.edge_from_json(edge) for edge in topology['edges']]
            streams = [Stream.from_json(stream, [node['name'] for node in nodes]) for stream in topology['streams']]

            topology_instance = Topology(str(topology['name']), str(topology.get('description', '')))

            for node in nodes:
                topology_instance.add_node(
                    name=node['name'],
                    processing_delay=node['processing_delay'],
                    processing_jitter=node['processing_jitter'],
                    sync_domain=node['sync_domain'],
                    sync_jitter=node['sync_jitter']
                )

                for port in node['ports']:
                    topology_instance.add_port_to_node(
                        node_name=node['name'],
                        port_name=port['name'],
                        gcl=port['gcl'],
                        gcl_cycle=port['gcl_cycle'],
                        gcl_open=port['gcl_open'],
                        gcl_offset=port['gcl_offset'],
                        express_priorities=port['express_priorities'],
                        gcl_priorities=port['gcl_priorities'],
                        frame_preemption=port['frame_preemption']
                    )
            for edge in edges:
                topology_instance.add_edge(
                    port_a=f'{edge["node1_name"]}-{edge["port1_name"]}',
                    port_b=f'{edge["node2_name"]}-{edge["port2_name"]}',
                    link_speed=edge['link_speed'],
                    propagation_delay=edge['propagation_delay'],
                    transmission_jitter=edge['transmission_jitter'],
                    max_frame_size=edge['max_frame_size']
                )

            topology_instance.add_streams(streams)

            return topology_instance

        except TopologyParsingError:
            # We already "handled" this error
            raise
        except:
            # Unknown error
            raise TopologyParsingError('Error parsing topology')

    def from_toponame(self, scenario):
        window = 0 if "w0" in scenario else 20
        
        sp1 = True if "c101" in scenario else False
        sp1 = True if "c501" in scenario else sp1
        sp2 = True if "c102" in scenario else False
        sp2 = True if "c502" in scenario else sp2
        sp3 = True if "c103" in scenario else False
        sp3 = True if "c503" in scenario else sp3
        
        tas1_1 = True if "c201" in scenario else False
        tas1_2 = True if "c211" in scenario else False
        tas1_3 = True if "c221" in scenario else False
        
        tas2_1 = True if "c202" in scenario else False
        tas2_2 = True if "c212" in scenario else False
        tas2_3 = True if "c222" in scenario else False
        tas2_4 = True if "c232" in scenario else False
        tas2_5 = True if "c242" in scenario else False
        
        tas3_1 = True if "c203" in scenario else False
        tas3_2 = True if "c213" in scenario else False
        tas3_3 = True if "c223" in scenario else False
        tas3_4 = True if "c233" in scenario else False
        tas3_5 = True if "c243" in scenario else False
        
        fp1 = True if "c301" in scenario else False
        fp1 = True if "c701" in scenario else fp1
        fp2 = True if "c302" in scenario else False
        fp2 = True if "c701" in scenario else fp2
        fp3 = True if "c303" in scenario else False
        fp3 = True if "c701" in scenario else fp3
        
        sync1 = "1" if "1-sTrue-" in scenario else "0"
        sync2 = "1" if "2-sTrue-" in scenario else "2"
        
        all_bc = []
        all_wc = []
        
        CT = 100000 # 100µs

        #for offset in range(0, window, 1):
        #topo = topology.Topology("tmp")


        talker = self.add_node("talker", sync_domain=sync1, processing_delay=2000)
        t_1 = self.add_port_to_node("talker", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)

        listener = self.add_node("listener", sync_domain=sync2)
        l_1 = self.add_port_to_node("listener", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)



        switch_one   = self.add_node("switch 1", sync_domain=sync1, processing_delay=1000, processing_jitter=80)
        if tas1_1:
            s1_1 = self.add_port_to_node("switch 1", "1", gcl=True, gcl_offset=10000, gcl_open=55000, gcl_cycle=CT, gcl_priorities=[7])
        elif tas1_2:
            s1_1 = self.add_port_to_node("switch 1", "1", gcl=True, gcl_offset=30000, gcl_open=55000, gcl_cycle=CT, gcl_priorities=[7])
        elif tas1_3:
            s1_1 = self.add_port_to_node("switch 1", "1", gcl=True, gcl_offset=15000, gcl_open=20000, gcl_cycle=CT/2, gcl_priorities=[7])
        elif fp1:
            s1_1 = self.add_port_to_node("switch 1", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT, express_priorities=[7], frame_preemption=True)
        else:
            s1_1 = self.add_port_to_node("switch 1", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT, express_priorities=[], gcl_priorities=[7, 6, 5, 4, 3, 2, 1, 0])
        s1_2 = self.add_port_to_node("switch 1", "2", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)
        s1_3 = self.add_port_to_node("switch 1", "3", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)



        switch_two   = self.add_node("switch 2", sync_domain="1", processing_delay=1000, processing_jitter=80)
        if tas2_1:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl=True, gcl_offset=5000,  gcl_open=25000, gcl_cycle=CT, gcl_priorities=[7])
        elif tas2_2:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl=True, gcl_offset=25000, gcl_open=55000, gcl_cycle=CT, gcl_priorities=[7])
        elif tas2_3:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl=True, gcl_offset=25000, gcl_open=80000, gcl_cycle=CT*2, gcl_priorities=[7])
        elif tas2_4:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl=True, gcl_offset=25000, gcl_open=80000, gcl_cycle=CT*3, gcl_priorities=[7])
        elif tas2_5:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl=True, gcl_offset=5000, gcl_open=80000, gcl_cycle=CT, gcl_priorities=[7])
        elif fp2:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT, express_priorities=[7], frame_preemption=True)
        else:
            s2_1 = self.add_port_to_node("switch 2", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT, express_priorities=[], gcl_priorities=[7, 6, 5, 4, 3, 2, 1, 0])
        s2_2 = self.add_port_to_node("switch 2", "2", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)
        s2_3 = self.add_port_to_node("switch 2", "3", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)



        switch_three = self.add_node("switch 3", sync_domain=sync2, processing_delay=1000, processing_jitter=80)
        if tas3_1:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl=True, gcl_offset=80000, gcl_open=15000, gcl_cycle=CT, gcl_priorities=[7, 6, 5])
        elif tas3_2:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl=True, gcl_offset=10000, gcl_open=45000, gcl_cycle=CT, gcl_priorities=[7, 6, 5])
        elif tas3_3:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl=True, gcl_offset=10000, gcl_open=30000, gcl_cycle=75000, gcl_priorities=[7, 6, 5])
        elif tas3_4:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl=True, gcl_offset=10000, gcl_open=10000, gcl_cycle=CT*2, gcl_priorities=[7])
        elif tas3_5:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl=True, gcl_offset=80000, gcl_open=10000, gcl_cycle=CT, gcl_priorities=[7])
        elif fp3:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT, express_priorities=[7], frame_preemption=True)
        else:
            s3_1 = self.add_port_to_node("switch 3", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT, express_priorities=[], gcl_priorities=[7, 6, 5, 4, 3, 2, 1, 0])
        s3_2 = self.add_port_to_node("switch 3", "2", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)
        s3_3 = self.add_port_to_node("switch 3", "3", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)


        
        stream_2 = self.add_node("stream 2", sync_domain=None)
        str_2 = self.add_port_to_node("stream 2", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)
        stream_3 = self.add_node("stream 3", sync_domain=None)
        str_3 = self.add_port_to_node("stream 3", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)
        stream_4 = self.add_node("stream 4", sync_domain=None)
        str_4 = self.add_port_to_node("stream 4", "1", gcl_offset=0, gcl_open=CT, gcl_cycle=CT)



        self.add_edge(t_1, s1_2)
        if "c501" in scenario or "c701" in scenario:
            self.add_edge(s1_1, s2_2, link_speed=100, max_frame_size=300)
        else:
            self.add_edge(s1_1, s2_2)
            
        if "c502" in scenario or "c702" in scenario:
            self.add_edge(s2_1, s3_2, link_speed=100, max_frame_size=300)
        else:
            self.add_edge(s2_1, s3_2)
            
        if "c503" in scenario or "c703" in scenario:
            self.add_edge(s3_1, l_1, link_speed=100, max_frame_size=300)
        else:
            self.add_edge(s3_1, l_1)
        
        self.add_edge(str_2, s1_3)
        self.add_edge(str_3, s2_3)
        self.add_edge(str_4, s3_3)
        #topo.add_edge(s3_1, l_1)


        stream_size_1 = 1000
        stream_size_2 = 1000
        stream_size_3 = 1000
        if "c501" in scenario or "c701" in scenario:
            stream_size_1 = 500
            #stream_size_2 = 450

        if "c502" in scenario or "c702" in scenario:
            stream_size_2 = 500

        if "c503" in scenario or "c703" in scenario:
            stream_size_3 = 500
            
        
        if "c501" in scenario or "c502" in scenario or "c503" in scenario or "c701" in scenario or "c702" in scenario or "c703" in scenario:
            stream_size = 100
        else:
            stream_size = 1000


        if "c501" in scenario or "c502" in scenario or "c701" in scenario or "c702" in scenario:
            stream1 = Stream(cycletime=CT, offset=10000, framesize=200, sender="talker", receiver="listener", priority=7, name="Stream 1", transmission_window=(window+1)*1000) 
        else:
            stream1 = Stream(cycletime=CT, offset=10000, framesize=200, sender="talker", receiver="listener", priority=7, name="Stream 1", transmission_window=(window+1)*1000) 
            

        stream2 = Stream(cycletime=CT, offset=0, framesize=stream_size_1, sender="stream 2", receiver="stream 3", priority=7, name="Stream 2", transmission_window=1) 
        stream3 = Stream(cycletime=CT, offset=0, framesize=stream_size_2, sender="stream 3", receiver="stream 4", priority=7, name="Stream 3", transmission_window=1) 
        stream4 = Stream(cycletime=CT, offset=0, framesize=stream_size_3, sender="stream 4", receiver="listener", priority=7, name="Stream 4", transmission_window=1) 

        self.add_streams([stream1, stream2, stream3, stream4])
 