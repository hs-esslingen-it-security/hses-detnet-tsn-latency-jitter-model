from math import ceil
from typing import List, TypedDict
from unicodedata import name
from jitter_delay_model.helpers import TopologyParsingError, Priority
# from topology import Topology, TopologyParsingError
import networkx as nx

class StreamJson(TypedDict):
    name: str
    cycleTime: int
    """Cycle time in nanoseconds"""
    offset: int
    """Offset in nanoseconds"""
    transmissionWindow: int
    """Transmission window in nanoseconds.
    Added to offset to calculate the transmission window.
    """
    frameSize: int
    """Frame size of the frames of the stream in bytes"""
    sender: str
    """Name of the node that is the sender of the stream"""
    receiver: str
    """Name of the node that is the receiver of the stream"""
    priority: Priority
    """Priority of the stream"""


class Stream:
    def __init__(
        self,
        name: str,
        cycletime: int,
        offset: int,
        transmission_window: int,
        framesize: int,
        sender: str,
        receiver: str,
        # topology: Topology,
        priority: Priority = 6
    ):
        self.name = name
        self.cycletime = cycletime
        self.offset = offset
        self.transmission_window = transmission_window
        self.priority: Priority = priority
        self.framesize = framesize
        self.sender = sender
        self.receiver = receiver
        # self.topology = topology
        # self.path = nx.shortest_path(topology.G, self.sender, self.receiver)
        # self.topology.add_streams([self])
        # self.bandwidth_per_node = {}
        # self.best_case: StreamDelay = {}
        # self.worst_case: StreamDelay = {}
        """The actually required bandwidth on a node in bytes"""
        # self.window_per_node: dict[str, int] = {}
        # """Overrides the window size defined by a node
        # key = node name, value = window size in nanoseconds
        # """
        self.saved_multiplications = []

    def to_json(self) -> StreamJson:
        stream: StreamJson = {}
        stream['name'] = self.name
        stream['cycleTime'] = self.cycletime
        stream['offset'] = self.offset
        stream['transmissionWindow'] = self.transmission_window
        stream['frameSize'] = self.framesize
        stream['sender'] = self.sender
        stream['receiver'] = self.receiver
        stream['priority'] = self.priority

        return stream

    def from_json(stream: dict, existing_nodes: List[str]) -> 'Stream':
        """
        @param stream JSON as dict to convert to Stream
        @param existing_nodes Names of the nodes that exist (to validate sender and receiver)
        """
        try:
            if 'name' not in stream:
                raise TopologyParsingError('Missing "name" key in stream')
            name = str(stream['name'])

            try:
                cycle_time = int(stream['cycleTime'])
            except:
                raise TopologyParsingError(f'Missing or invalid key "cycleTime" in stream {name}')

            offset = int(stream.get('offset', 0))
            transmission_window = int(stream.get('transmissionWindow', 0))

            try:
                frame_size = int(stream['frameSize'])
            except:
                raise TopologyParsingError(f'Missing or invalid key "frameSize" in stream {name}')

            try:
                sender = str(stream['sender'])
            except:
                raise TopologyParsingError(f'Missing or invalid key "sender" in stream {name}')
            
            if (sender not in existing_nodes):
                raise TopologyParsingError(f'Node {sender}, which was given as sender in stream {name}, does not exist')

            try:
                receiver = str(stream['receiver'])
            except:
                raise TopologyParsingError(f'Missing or invalid key "receiver" in stream {name}')
            
            if (receiver not in existing_nodes):
                raise TopologyParsingError(f'Node {receiver}, which was given as receiver in stream {name}, does not exist')

            priority = int(stream.get('priority', 0))

            if (priority < 0 or priority > 7):
                raise TopologyParsingError(f'Invalid priority "{priority}" given in stream {name}')
        except TopologyParsingError:
            # We already "handled" this error
            raise
        except:
            # Unknown error
            raise TopologyParsingError(f'Error parsing stream "{name}"')
        
        return Stream(
            name=name,
            cycletime=cycle_time,
            offset=offset,
            transmission_window=transmission_window,
            framesize=frame_size,
            sender=sender,
            receiver=receiver,
            priority=priority
        )
