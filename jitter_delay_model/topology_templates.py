from typing import Dict, Tuple
from jitter_delay_model.calculator import Calculator
from jitter_delay_model.helpers import StreamStatistics, get_summarized_delay
from jitter_delay_model.stream import Stream
from jitter_delay_model.topology import Topology


def use_topology_a1(topology_dict: dict) -> Tuple[Dict[str, StreamStatistics], Topology]:
    """Topology for the paper"""
    t2 = Topology.from_json(topology_dict)

    # t2.add_node("node 0", sync_domain="1")
    # p0_0 = t2.add_port_to_node("node 0", "0", gcl_open=30000)

    # t2.add_node("node 1", sync_domain="1")
    # p1_0 = t2.add_port_to_node("node 1", "0", gcl_offset=40000, gcl_open=30000)
    # p1_1 = t2.add_port_to_node("node 1", "1", gcl_offset=40000, gcl_open=30000)

    # t2.add_node("node 2", sync_domain="1")
    # p2_0 = t2.add_port_to_node("node 2", "0", gcl_offset=80000, gcl_open=30000)
    # p2_1 = t2.add_port_to_node("node 2", "1", gcl_offset=80000, gcl_open=30000)
    # p2_2 = t2.add_port_to_node("node 2", "2", gcl_offset=80000, gcl_open=30000)

    # t2.add_node("node 3", sync_domain="1")
    # p3_0 = t2.add_port_to_node("node 3", "0", gcl_offset=120000, gcl_open=30000)
    # p3_1 = t2.add_port_to_node("node 3", "1", gcl_offset=120000, gcl_open=30000)
    # p3_2 = t2.add_port_to_node("node 3", "2", gcl_offset=120000, gcl_open=30000)
    # p3_3 = t2.add_port_to_node("node 3", "3", gcl_offset=120000, gcl_open=30000)

    # # source for node 2
    # t2.add_node("node 4", sync_domain="1")
    # p4_0 = t2.add_port_to_node("node 4", "0", gcl_offset=40000, gcl_open=30000)

    # # source for node 3
    # t2.add_node("node 5", sync_domain="1")
    # p5_0 = t2.add_port_to_node("node 5", "0", gcl_offset=80000, gcl_open=30000)

    # # sink for node 3 (Path 2)
    # t2.add_node("node 6", sync_domain="1")
    # p6_0 = t2.add_port_to_node("node 6", "0")

    # # sink for node 3 (Path 1, 3)
    # t2.add_node("node 7", sync_domain="1")
    # p7_0 = t2.add_port_to_node("node 7", "0")

    # t2.add_edge(p0_0, p1_0)

    # t2.add_edge(p1_1, p2_0)
    # t2.add_edge(p4_0, p2_2)

    # t2.add_edge(p2_1, p3_0)
    # t2.add_edge(p5_0, p3_3)

    # t2.add_edge(p3_1, p6_0)

    # t2.add_edge(p3_2, p7_0)

    # s1 = Stream('Stream 1', cycletime=1000000, offset=0, framesize=500, sender="node 0", receiver="node 7", topology=t2, priority=6)
    # s2 = Stream('Stream 2', cycletime=1000000, offset=0, framesize=64, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s3 = Stream('Stream 3', cycletime=1000000, offset=0, framesize=570, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s4 = Stream('Stream 4', cycletime=1000000, offset=0, framesize=1518, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s5 = Stream('Stream 5', cycletime=1000000, offset=0, framesize=64, sender="node 5", receiver="node 7", topology=t2, priority=7)
    # s6 = Stream('Stream 6', cycletime=1000000, offset=0, framesize=570, sender="node 5", receiver="node 7", topology=t2, priority=7)
    # s7 = Stream('Stream 7', cycletime=1000000, offset=0, framesize=1518, sender="node 5", receiver="node 7", topology=t2, priority=7)

    # streams = [s1, s2, s3, s4, s5, s6, s7]

    calculator = Calculator(topology=t2, streams=t2.streams)

    calculator.get_best_case()
    calculator.get_worst_case()

    
    calculator.recalculate_bandwidth()
    
    calculator.recalculate_bandwidth()


    calculator.get_best_case()
    calculator.get_worst_case()

    calculator.get_resource_utilization()


    # return stream of interest (the first one), topology
    return calculator.stream_statistics, t2


def use_topology_a2(topology_dict: dict) -> Tuple[Dict[str, StreamStatistics], Topology]:
    """Topology for the paper"""
    t2 = Topology.from_json(topology_dict)

    # t2.add_node("node 0", sync_domain="1")
    # p0_0 = t2.add_port_to_node("node 0", "0", gcl_open=30000)

    # t2.add_node("node 1", sync_domain="1")
    # p1_0 = t2.add_port_to_node("node 1", "0", gcl_offset=40000, gcl_open=30000)
    # p1_1 = t2.add_port_to_node("node 1", "1", gcl_offset=40000, gcl_open=30000)

    # t2.add_node("node 2", sync_domain="1")
    # p2_0 = t2.add_port_to_node("node 2", "0", gcl_offset=80000, gcl_open=30000)
    # p2_1 = t2.add_port_to_node("node 2", "1", gcl_offset=80000, gcl_open=30000)
    # p2_2 = t2.add_port_to_node("node 2", "2", gcl_offset=80000, gcl_open=30000)

    # t2.add_node("node 3", sync_domain="1")
    # p3_0 = t2.add_port_to_node("node 3", "0", gcl_offset=120000, gcl_open=30000)
    # p3_1 = t2.add_port_to_node("node 3", "1", gcl_offset=120000, gcl_open=30000)
    # p3_2 = t2.add_port_to_node("node 3", "2", gcl_offset=120000, gcl_open=30000)
    # p3_3 = t2.add_port_to_node("node 3", "3", gcl_offset=120000, gcl_open=30000)

    # # source for node 2
    # t2.add_node("node 4", sync_domain="1")
    # p4_0 = t2.add_port_to_node("node 4", "0", gcl_offset=40000, gcl_open=30000)

    # # source for node 3
    # t2.add_node("node 5", sync_domain="1")
    # p5_0 = t2.add_port_to_node("node 5", "0", gcl_offset=80000, gcl_open=30000)

    # # sink for node 3 (Path 2)
    # t2.add_node("node 6", sync_domain="1")
    # p6_0 = t2.add_port_to_node("node 6", "0")

    # # sink for node 3 (Path 1, 3)
    # t2.add_node("node 7", sync_domain="1")
    # p7_0 = t2.add_port_to_node("node 7", "0")

    # t2.add_edge(p0_0, p1_0)

    # t2.add_edge(p1_1, p2_0)
    # t2.add_edge(p4_0, p2_2)

    # t2.add_edge(p2_1, p3_0)
    # t2.add_edge(p5_0, p3_3)

    # t2.add_edge(p3_1, p6_0)

    # t2.add_edge(p3_2, p7_0)

    # s1 = Stream(cycletime=1000000, offset=0, framesize=500, sender="node 0", receiver="node 7", topology=t2, priority=6)
    # s2 = Stream(cycletime=330000, offset=0, framesize=64, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s3 = Stream(cycletime=330000, offset=0, framesize=570, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s4 = Stream(cycletime=330000, offset=0, framesize=1518, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s5 = Stream(cycletime=330000, offset=0, framesize=64, sender="node 5", receiver="node 7", topology=t2, priority=7)
    # s6 = Stream(cycletime=330000, offset=0, framesize=570, sender="node 5", receiver="node 7", topology=t2, priority=7)
    # s7 = Stream(cycletime=330000, offset=0, framesize=1518, sender="node 5", receiver="node 7", topology=t2, priority=7)

    # streams = [s1, s2, s3, s4, s5, s6, s7]

    calculator = Calculator(t2, t2.streams)

    calculator.get_best_case()
    calculator.get_worst_case()

    
    calculator.recalculate_bandwidth()
    
    calculator.recalculate_bandwidth()


    calculator.get_best_case()
    calculator.get_worst_case()

    calculator.get_resource_utilization()


    # return stream of interest (the first one), topolgy
    return calculator.stream_statistics, t2


def use_topology_a3(topology_dict: dict) -> Tuple[Dict[str, StreamStatistics], Topology]:
    """Topology for the paper"""
    t2 = Topology.from_json(topology_dict)

    # t2.add_node("node 0", sync_domain="1")
    # p0_0 = t2.add_port_to_node("node 0", "0", gcl_open=30000)

    # t2.add_node("node 1", sync_domain="1")
    # p1_0 = t2.add_port_to_node("node 1", "0", gcl_offset=40000, gcl_open=30000)
    # p1_1 = t2.add_port_to_node("node 1", "1", gcl_offset=40000, gcl_open=30000)

    # t2.add_node("node 2", sync_domain="2")
    # p2_0 = t2.add_port_to_node("node 2", "0", gcl_offset=80000, gcl_open=30000)
    # p2_1 = t2.add_port_to_node("node 2", "1", gcl_offset=80000, gcl_open=30000)
    # p2_2 = t2.add_port_to_node("node 2", "2", gcl_offset=80000, gcl_open=30000)

    # t2.add_node("node 3", sync_domain="2")
    # p3_0 = t2.add_port_to_node("node 3", "0", gcl_offset=120000, gcl_open=30000)
    # p3_1 = t2.add_port_to_node("node 3", "1", gcl_offset=120000, gcl_open=30000)
    # p3_2 = t2.add_port_to_node("node 3", "2", gcl_offset=120000, gcl_open=30000)
    # p3_3 = t2.add_port_to_node("node 3", "3", gcl_offset=120000, gcl_open=30000)

    # # source for node 2
    # t2.add_node("node 4", sync_domain="2")
    # p4_0 = t2.add_port_to_node("node 4", "0", gcl_offset=40000, gcl_open=30000)

    # # source for node 3
    # t2.add_node("node 5", sync_domain="2")
    # p5_0 = t2.add_port_to_node("node 5", "0", gcl_offset=80000, gcl_open=30000)

    # # sink for node 3 (Path 2)
    # t2.add_node("node 6", sync_domain="2")
    # p6_0 = t2.add_port_to_node("node 6", "0")

    # # sink for node 3 (Path 1, 3)
    # t2.add_node("node 7", sync_domain="2")
    # p7_0 = t2.add_port_to_node("node 7", "0")

    # t2.add_edge(p0_0, p1_0)

    # t2.add_edge(p1_1, p2_0)
    # t2.add_edge(p4_0, p2_2)

    # t2.add_edge(p2_1, p3_0)
    # t2.add_edge(p5_0, p3_3)

    # t2.add_edge(p3_1, p6_0)

    # t2.add_edge(p3_2, p7_0)

    # s1 = Stream(cycletime=1000000, offset=0, framesize=500, sender="node 0", receiver="node 7", topology=t2, priority=6)
    # s2 = Stream(cycletime=1000000, offset=0, framesize=64, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s3 = Stream(cycletime=1000000, offset=0, framesize=570, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s4 = Stream(cycletime=1000000, offset=0, framesize=1518, sender="node 4", receiver="node 6", topology=t2, priority=6)
    # s5 = Stream(cycletime=1000000, offset=0, framesize=64, sender="node 5", receiver="node 7", topology=t2, priority=7)
    # s6 = Stream(cycletime=1000000, offset=0, framesize=570, sender="node 5", receiver="node 7", topology=t2, priority=7)
    # s7 = Stream(cycletime=1000000, offset=0, framesize=1518, sender="node 5", receiver="node 7", topology=t2, priority=7)

    # streams = [s1, s2, s3, s4, s5, s6, s7]
    
    calculator = Calculator(t2, t2.streams)

    calculator.get_best_case()
    calculator.get_worst_case()
    
    calculator.recalculate_bandwidth()

    calculator.get_resource_utilization()

    # return stream of interest (the first one), topology
    return calculator.stream_statistics, t2