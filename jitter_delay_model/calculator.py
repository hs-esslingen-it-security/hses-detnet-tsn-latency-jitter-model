import json
from math import ceil
from typing import List
import networkx as nx
from jitter_delay_model.path_helpers import get_ancestor_tx_port_node_name, is_rx_port, is_tx_port
from jitter_delay_model.path_helpers import get_ancestor_forwarding_node_name
from jitter_delay_model.helpers import ExpressPriorities, PortStatistics, StreamStatistics, debug, get_transmission_duration
from jitter_delay_model.stream import Stream
from jitter_delay_model.topology import NodeAttrs, Topology

class Calculator:
    def __init__(self, topology: Topology, streams: List[Stream]) -> None:
        """
        @param streams All streams on the topology
        """
        self.topology = topology
        self.streams = streams
        self.stream_paths: dict[str, List[str]] = {}
        """Shortest path based on the given topology for each stream.

        - key = stream name
        - value = path (list of node names)
        """

        self.bandwidth_per_stream_and_node: dict[str, dict[str, int]] = {}
        """Outer dict is addressed using stream name, inner dict using the node name"""

        self.stream_statistics: dict[str, StreamStatistics] = {}
        """Statistics (delays, resource utilization) per stream with the stream name as key
        """

        for stream in streams:
            self.stream_paths[stream.name] = nx.shortest_path(topology.G, stream.sender, stream.receiver)
            self.stream_statistics[stream.name] = StreamStatistics(stream.name, self.stream_paths[stream.name], self.topology.G.nodes(data=True))

    def get_crossing_streams(self, observed_stream_name: str, port_node_name: str) -> List[Stream]:
        """Returns streams that cross the same given port
        @param observed_stream_name Stream that is crossed by the other streams (is not added to the returned list)
        @param port_name Name of the port node (full name including forwarding node name)
        """
        crossing_streams = [stream for stream in self.streams if port_node_name in self.stream_paths[stream.name] and stream.name != observed_stream_name]
        return crossing_streams

    def get_interfering_streams(self, observed_stream: Stream, port_name: str) -> List[Stream]:
        """Returns streams that interfere with this stream on the given port
        Interfering streams cross the same port and have the same or a higher priority.
        @param observed_stream Stream that is interfered by the other streams (is not added to the returned list)
        @param port_name Name of the port node
        """
        express_priorities: ExpressPriorities = self.topology.G.nodes(data=True)[port_name]["express_priorities"]
        crossing_streams = self.get_crossing_streams(observed_stream.name, port_name)

        if observed_stream.priority in express_priorities:
            interfering_streams = [
                stream for stream in crossing_streams
                    if stream.priority >= observed_stream.priority and stream.priority in express_priorities
            ]
        else:
            interfering_streams = [
                stream for stream in crossing_streams
                    if stream.priority in express_priorities or stream.priority >= observed_stream.priority
            ]

        return interfering_streams

    def get_bandwidth(self, stream: Stream, node_name: str) -> int:
        """Returns the bandwidth in bytes of this stream on the given node.
        Ensure that the given node is no forwarding node
        """
        if stream.name not in self.bandwidth_per_stream_and_node:
            return stream.framesize

        return self.bandwidth_per_stream_and_node[stream.name].get(node_name, stream.framesize)

    def set_bandwidth(self, stream: Stream, node_name: str, bandwidth: int):
        """Set a new bandwidth for the given stream on the given node in bytes"""
        if self.get_bandwidth(stream, node_name) < bandwidth:
            if stream.name not in self.bandwidth_per_stream_and_node:
                self.bandwidth_per_stream_and_node[stream.name] = {}
            self.bandwidth_per_stream_and_node[stream.name][node_name] = bandwidth

    def get_new_bandwidth(self, stream: Stream, d_arriv: int, node_a: str = None, node_b: str = None, ct_a: int = None, ct_b: int = None) -> int:
        """Calculates the new bandwidth in bytes required in domain B if the stream flows from domain A (node_a) to domain B (node_b).
        Ensure that the given nodes are no forwarding nodes. Instead of a node, a cycle time can be passed.

        @param d_arriv arrival window (worst case - best case)
        """

        if isinstance(node_a, str):
            node_a_data: NodeAttrs = self.topology.G.nodes(data=True)[node_a]
            ct_a = node_a_data["gcl_cycle"]

        if isinstance(node_b, str):
            node_b_data: NodeAttrs = self.topology.G.nodes(data=True)[node_b]
            ct_b = node_b_data["gcl_cycle"]

        factor_arriv = ceil(d_arriv / ct_b)
        factor_ct = ceil(ct_b / ct_a)
        new_bandwidth = self.get_bandwidth(stream, node_a) * factor_arriv * factor_ct
        return new_bandwidth

    def recalculate_bandwidth_for_stream(self, stream: Stream, stream_statistics: StreamStatistics):
        """Calculates the new bandwidth of the given stream for each node on the path based on the already calculated best case and worst case delays"""
        debug(f'Recalculating bandwidth for stream {stream.name}')

        path = self.stream_paths[stream.name]
        all_nodes = self.topology.G.nodes(data=True)

        debug(f"Old (already modified) bandwidth: {self.bandwidth_per_stream_and_node.get(stream.name, None)}")
        for index, node_name in enumerate(path):
            node_data = all_nodes[node_name]

            if index == 0 or node_data["forwarding_node"]:
                continue
            if index == len(path)-1:
                break
            if is_rx_port(node_name, None, path):
                continue

            forwarding_node_name = get_ancestor_forwarding_node_name(path=self.stream_paths[stream.name], node_index=index)
            ancestor_port_node_name = get_ancestor_tx_port_node_name(path=self.stream_paths[stream.name], node_index=index)

            if ancestor_port_node_name is None and index != 1:
                continue
        
            best_case_sum = stream_statistics.get_summarized_best_case(f'{forwarding_node_name}-tx')
            worst_case_sum = stream_statistics.get_summarized_worst_case(f'{forwarding_node_name}-tx')
            d_arriv = worst_case_sum - best_case_sum

            if index == 1:
                # In this case, there is no previous domain. Use stream cycle time instead
                new_bandwidth = self.get_new_bandwidth(stream, d_arriv, None, node_name, ct_a=stream.cycletime)
            else:
                new_bandwidth = self.get_new_bandwidth(stream, d_arriv, ancestor_port_node_name, node_name)

            self.set_bandwidth(stream, node_name, new_bandwidth)
        debug(f"New (already modified) bandwidth: {self.bandwidth_per_stream_and_node.get(stream.name, None)}")

    def recalculate_bandwidth(self, streams: List[str] = None):
        """
        @param streams Name of the streams for which the bandwidth should be calculated.
        Note: all streams that exist on the topology should be calculated
        """
        for stream in self.streams:
            if streams is not None and len([s for s in streams if s == stream.name]) == 0:
                continue

            self.recalculate_bandwidth_for_stream(stream, self.stream_statistics[stream.name])

    def get_stream_transmission_duration(self, stream: Stream, link_speed: int, node_name: str) -> int:
        """Calculates transmission duration of the stream based on the link speed (including L1 overhead)

        @link_speed Link speed in Mbit/s

        @returns Transmission duration in nanoseconds
        """
        # TODO: what was the reason to use the bandwidth here?
        framesize = self.get_bandwidth(stream, node_name) if node_name is not None else stream.framesize
        return get_transmission_duration(framesize + 20, link_speed)

    def calculate_delays_for_stream(self, stream: Stream):
        path = self.stream_paths[stream.name]
        all_nodes = self.topology.G.nodes(data=True)
        all_edges = self.topology.G.edges(data=True)

        best_case = [("init", stream.offset, stream.offset+stream.transmission_window, 0, 0)]
        worst_case = [("init", stream.offset, stream.offset+stream.transmission_window, 0, 0, stream.cycletime)]
        multiplication = []

        stream_statistics = self.stream_statistics[stream.name]
        stream_statistics.clear_best_case()
        stream_statistics.clear_worst_case()

        for index, node_name in enumerate(path):
            try:
                port_statistics = stream_statistics.get_port_statistics(node_name)
            except:
                port_statistics = None

            node_data = all_nodes[node_name]

            if is_rx_port(node_name, None, path):
                multiplication.append(1)
                continue

            if node_data["forwarding_node"]:
                # Section 5.2.1 Processing Delay
                d_proc = node_data["processing_delay"]
                d_proc_bc = d_proc - node_data["processing_jitter"]
                d_proc_wc = d_proc + node_data["processing_jitter"]

                multiplication.append(1)
                best_case.append((node_name, best_case[-1][1]+d_proc_bc, best_case[-1][2]+d_proc_bc, best_case[-1][3]+d_proc_bc, best_case[-1][4]+d_proc_bc))
                worst_case.append((node_name, worst_case[-1][1]+d_proc_wc, worst_case[-1][2]+d_proc_wc, worst_case[-1][3]+d_proc_wc, worst_case[-1][3]+d_proc_wc, 0))
            else:
                forwarding_node_name = self.topology.get_forwarding_node_name_by_port(node_name)
                forwarding_node_data = all_nodes[forwarding_node_name]
                edge = self.topology.G.get_edge_data(node_name, path[index+1])
                ancestor_forwarding_node_name = get_ancestor_forwarding_node_name(path, node_index=index)
                is_synchronized = self.topology.are_synchronized(forwarding_node_name, ancestor_forwarding_node_name) if ancestor_forwarding_node_name is not None else True


                # Section 5.2.2 Propagation Delay
                d_prop = edge["propagation_delay"]

                # Section 5.2.3 Transmission Delay
                d_trans = self.get_stream_transmission_duration(stream, edge["link_speed"], None)
                d_trans_bc = d_trans - edge["transmission_jitter"] + d_prop
                d_trans_wc = d_trans + edge["transmission_jitter"] + d_prop

                # Section 5.2.4 Interference Delay
                # Equation 1
                interfering_streams = self.get_interfering_streams(stream, node_name)
                interfering_streams = [s for s in interfering_streams if s.priority >= stream.priority]

                # Equation 2
                if node_data["frame_preemption"]:
                    express_priorities = node_data["express_priorities"]
                    if len(express_priorities) != 0:
                        interfering_streams = [s for s in interfering_streams if s.priority in express_priorities]

                # Equation 3
                if node_data["gcl"]:
                    gcl_priorities = node_data["gcl_priorities"]
                    if len(gcl_priorities) != 0:
                        interfering_streams = [s for s in interfering_streams if s.priority in gcl_priorities]
                
                # Equation 4
                # TODO: different cycle times!!
                interfering_streams_delays = [self.get_stream_transmission_duration(s, edge["link_speed"], node_name) + edge["transmission_jitter"] for s in interfering_streams]
                # do not assume interference on the sender
                # TODO: handle talker with index of node
                d_interference = sum(interfering_streams_delays) if "talker" not in node_name else 0

                # Equations 15 and 17
                d_interference *= ceil(worst_case[-2][5]/stream.cycletime)


                # Section 5.2.5 Blocking Delay 
                # calculate blocking delay (including L1 overhead, beacause the used function does not add the L1 overhead itself)
                if node_data["frame_preemption"]:
                    express_priorities = node_data["express_priorities"]
                else:
                    express_priorities = []

                if node_data["gcl"]:
                    gcl_priorities = node_data["gcl_priorities"]
                else:
                    gcl_priorities = [0, 1, 2, 3, 4, 5, 6, 7]

                if stream.priority in express_priorities:
                    blck_bytes = 123 + 20
                else:
                    blck_bytes = edge["max_frame_size"] + 20
                    
                if len([_ for _ in gcl_priorities if _ < stream.priority]) == 0:
                    blck_bytes = 0
                    
                # do not assume blocking on the sender
                # TODO: handle talker with index of node
                d_blck = get_transmission_duration(blck_bytes, edge["link_speed"]) if "talker" not in node_name else 0
                

                # Equation 8 + influence of changing cycle time
                #d_dwell = d_trans_wc + d_blck + d_interference + max(0, worst_case[-2][5]-node_data["gcl_cycle"])
                d_dwell = d_trans_wc + d_blck + max(0, worst_case[-2][5]-node_data["gcl_cycle"])
                
                
                if node_data["gcl"]:
                    multiplication.append(node_data["gcl_cycle"]/max(1, worst_case[-2][5]))
                else:
                    multiplication.append(1)
                    
                
                # TAS
                if node_data["gcl"]:
                    
                    # synchronized and domain before also was a TAS domain
                    if is_synchronized and best_case[-1][1] != -1:
                        # best case scenario
                        ## is the beginning of the transmission window before the gate open?
                        early_1 = node_data["gcl_offset"] - (best_case[-1][1] % node_data["gcl_cycle"])
                        early_2 = node_data["gcl_offset"] - (best_case[-1][2])# % node_data["gcl_cycle"])
                        ## how much space is left after the beginning of the transmission window in the TAS window?
                        remaining_1 = (node_data["gcl_offset"]+node_data["gcl_open"]) - (best_case[-1][1] % node_data["gcl_cycle"])
                        ## how much space is left after the end of the transmission window in the TAS window?
                        remaining_2 = (node_data["gcl_offset"]+node_data["gcl_open"]) - (best_case[-1][2] % node_data["gcl_cycle"])

                        # is the beginning before the TAS open?
                        if early_1 >= 0:
                            if early_2 >= 0:
                                ##best_case.append((node_name, best_case[-1][1]+early_1+d_trans_bc, best_case[-1][2]+early_2+d_trans_bc, best_case[-1][3]+early_1+d_trans_bc-forwarding_node_data["sync_jitter"], best_case[-1][4]+early_2+d_trans_bc-forwarding_node_data["sync_jitter"]))
                                d_gate_1 = early_1
                                d_gate_2 = early_2
                                
                                offset_correction_1 = 0
                                offset_correction_2 = 0
                            # is the end far enough ahead of the TAS close for a transmission
                            elif remaining_2 >= d_trans_bc:
                                d_gate_1 = early_1
                                d_gate_2 = 0
                                
                                offset_correction_1 = 0
                                offset_correction_2 = 0
                                ##best_case.append((node_name, best_case[-1][1]+early_1+d_trans_bc, best_case[-1][2]+d_trans_bc, best_case[-1][3]+early_1+d_trans_bc-forwarding_node_data["sync_jitter"], best_case[-1][4]+d_trans_bc-forwarding_node_data["sync_jitter"]))
                            else:
                                d_gate_1 = early_1
                                d_gate_2 = 0
                                
                                offset_correction_1 = 0
                                offset_correction_2 = -1*remaining_2
                                ##best_case.append((node_name, best_case[-1][1]+early_1+d_trans_bc, best_case[-1][2]+remaining_2, best_case[-1][3]+early_1+d_trans_bc-forwarding_node_data["sync_jitter"], best_case[-1][4]+remaining_2-forwarding_node_data["sync_jitter"]))
                        else:
                            # is the complete transmission window within the TAS window?
                            if remaining_1 >= d_trans_bc and remaining_2 >= d_trans_bc:
                                d_gate_1 = 0
                                d_gate_2 = 0  
                                
                                offset_correction_1 = 0
                                offset_correction_2 = 0                              
                                ##best_case.append((node_name, best_case[-1][1]+d_trans_bc, best_case[-1][2]+d_trans_bc, best_case[-1][3]+d_trans_bc-forwarding_node_data["sync_jitter"], best_case[-1][4]+d_trans_bc-forwarding_node_data["sync_jitter"]))
                            # is only the beginning of the transmission window in the TAS window?
                            elif remaining_1 >= d_trans_bc:
                                d_gate_1 = 0
                                d_gate_2 = 0    
                                
                                offset_correction_1 = 0
                                offset_correction_2 = 0                            
                                ##best_case.append((node_name, best_case[-1][1]+d_trans_bc, best_case[-1][2]+remaining_2, best_case[-1][3]+d_trans_bc-forwarding_node_data["sync_jitter"], best_case[-1][4]+d_trans_bc-forwarding_node_data["sync_jitter"]))
                            else:
                                d_gate_1 = 0
                                d_gate_2 = 0  
                                
                                offset_correction_1 = 0
                                offset_correction_2 = 0                              
                                # we miss the gate, so we calculate how long we need to wait until the end of this cycle
                                remaining_time_in_cycle_1 = node_data["gcl_cycle"]-(best_case[-1][1] % node_data["gcl_cycle"])
                                remaining_time_in_cycle_2 = node_data["gcl_cycle"]-(best_case[-1][2] % node_data["gcl_cycle"])
                                # transmit in the beginning of the next cycle --> window shrinks to size 0
                                ##best_case.append((node_name, best_case[-1][1]+remaining_time_in_cycle_1+node_data["gcl_offset"]+d_trans_bc, best_case[-1][2]+remaining_time_in_cycle_2+node_data["gcl_offset"]+d_trans_bc, best_case[-1][3]+remaining_time_in_cycle_1+node_data["gcl_offset"]+d_trans_bc, best_case[-1][4]+remaining_time_in_cycle_2+node_data["gcl_offset"]+d_trans_bc))
                        
                        
                        
                        
                        # Equation 13
                        d_forward_1 = d_gate_1+d_trans_bc-forwarding_node_data["sync_jitter"]
                        d_forward_2 = d_gate_2+d_trans_bc-forwarding_node_data["sync_jitter"]
                        best_case.append((node_name, best_case[-1][1]+d_forward_1+offset_correction_1, best_case[-1][2]+d_forward_2+offset_correction_2, best_case[-1][3]+d_forward_1, best_case[-1][4]+d_forward_2))

                                
                                
                                
                        # worst case scenario TAS

                        ## is the beginning of the transmission window after the gate close?
                        late_1 = (node_data["gcl_offset"]+node_data["gcl_open"] - (worst_case[-1][1] % node_data["gcl_cycle"]))
                        ## is the end of the transmission window after the gate close?
                        late_2 = (node_data["gcl_offset"]+node_data["gcl_open"] - (worst_case[-1][2] % node_data["gcl_cycle"]))

                        ## is the beginning of the transmission window before the gate open?
                        early_1 = (node_data["gcl_offset"] - (worst_case[-1][1] % node_data["gcl_cycle"]))
                        ## is the end of the transmission window before the gate open?
                        early_2 = (node_data["gcl_offset"] - (worst_case[-1][2] % node_data["gcl_cycle"]))

                        # is the end after the TAS close?
                        #if late_1 >= d_trans_wc and late_2 >= d_trans:
                        tmp = (d_trans+d_blck+d_interference)
                        if late_1 < tmp and late_2 < tmp:
                            # Equation 11 case 'otherwise' for the beginning of the transmission window
                            d_gate_1 = node_data["gcl_cycle"]-(worst_case[-1][1] % node_data["gcl_cycle"])+node_data["gcl_open"]
                            # Equation 11 case 'otherwise' for the end of the transmission window
                            d_gate_2 = node_data["gcl_cycle"]-(worst_case[-1][2] % node_data["gcl_cycle"])+node_data["gcl_open"]

                            # Equation 13
                            ##d_forward_1 = d_gate_1+d_trans+d_blck+d_interference
                            ##d_forward_2 = d_gate_2+d_trans+d_blck+d_interference

                            ##worst_case.append((node_name, worst_case[-1][1]+d_forward_1, worst_case[-1][2]+d_forward_2, worst_case[-1][3]+d_forward_1, worst_case[-1][4]+d_forward_2, node_data["gcl_cycle"]))

                        elif late_2 < tmp:
                            # we miss the gate, so we calculate how long we need to wait
                            d_gate_1 = 0#node_data["gcl_cycle"]-(worst_case[-1][1] % node_data["gcl_cycle"])

                            # Equation 11 case 'otherwise' for the end of the transmission window (additionally assume any transmission in the transmission window to be a longer worst-case)
                            d_gate_unsync = node_data["gcl_cycle"]-node_data["gcl_open"]+d_trans+(d_interference/max(1,len(interfering_streams)))
                            d_gate_2 = d_gate_unsync  + max(0, node_data["gcl_cycle"]-worst_case[-2][5]) #max(d_gate_unsync, node_data["gcl_cycle"]-(worst_case[-1][2] % node_data["gcl_cycle"]))
                            #d_gate_2 = node_data["gcl_cycle"]-(node_data["gcl_cycle"] % node_data["gcl_cycle"]))
                            #d_gate_2 = node_data["gcl_cycle"]-(worst_case[-1][2] % node_data["gcl_cycle"])

                            # Equation 13
                            ##d_forward_1 = d_gate_1+d_trans+d_blck#+d_interference
                            ##d_forward_2 = d_gate_2+d_trans+d_blck#+d_interference
                            
                            ##worst_case.append((node_name, worst_case[-1][1]+d_forward_1, worst_case[-1][2]+d_forward_2, worst_case[-1][3]+d_forward_1, worst_case[-1][4]+d_forward_2, node_data["gcl_cycle"]))
                        elif early_2 >= 0:
                            # Equation 11 case 'C1' for the beginning of the transmission window
                            d_gate_1 = early_1
                            # Equation 11 case 'C1' for the end of the transmission window
                            d_gate_2 = early_2
                            ##d_forward_1 = d_gate_1+d_trans+d_blck+d_interference
                            ##d_forward_2 = d_gate_2+d_trans+d_blck+d_interference
                            ##worst_case.append((node_name, worst_case[-1][1]d_forward_1, worst_case[-1][2]+d_forward_2, worst_case[-1][3]+d_forward_1, worst_case[-1][4]+d_forward_2, node_data["gcl_cycle"]))
                        elif early_1 >= 0:
                            # Equation 11 case 'C1' for the beginning of the transmission window
                            d_gate_1 = early_1
                            # Equation 11 case 'C2' for the end of the transmission window
                            d_gate_2 = 0
                            ##d_forward_1 = d_gate_1+d_trans+d_blck+d_interference
                            ##d_forward_2 = d_gate_2+d_trans+d_blck+d_interference
                            ##worst_case.append((node_name, worst_case[-1][1]+d_forward_1, worst_case[-1][2]+d_forward_2, worst_case[-1][3]+d_forward_1, worst_case[-1][4]+d_forward_2, node_data["gcl_cycle"]))
                        else:
                            # Equation 11 case 'C2' 
                            d_gate_1 = 0
                            d_gate_2 = 0
                            ##d_forward_1 = d_gate_1+d_trans+d_blck+d_interference
                            ##d_forward_2 = d_gate_2+d_trans+d_blck+d_interference
                            #worst_case.append((node_name, worst_case[-1][1]+d_dwell+d_interference, worst_case[-1][2]+d_dwell+d_interference, worst_case[-1][3]+d_dwell+d_interference, worst_case[-1][4]+d_dwell+d_interference, node_data["gcl_cycle"]))
                            ##worst_case.append((node_name, worst_case[-1][1]+d_forward_1, worst_case[-1][2]+d_forward_2, worst_case[-1][3]+d_forward_1, worst_case[-1][4]+d_forward_2, node_data["gcl_cycle"]))
                            
                        
                        # Equation 13
                        d_forward_1 = d_gate_1+d_trans+d_blck+d_interference+forwarding_node_data["sync_jitter"]+ max(0, node_data["gcl_cycle"]-worst_case[-2][5])
                        d_forward_2 = d_gate_2+d_trans+d_blck+d_interference+forwarding_node_data["sync_jitter"]+ max(0, node_data["gcl_cycle"]-worst_case[-2][5])
                        worst_case.append((node_name, worst_case[-1][1]+d_forward_1, worst_case[-1][2]+d_forward_2, worst_case[-1][3]+d_forward_1, worst_case[-1][4]+d_forward_2, node_data["gcl_cycle"]))

                            
                            
                            
                    # unsynchronized TAS
                    else:
                        # is the transmission window larger than the TAS window?
                        exceeding = (best_case[-1][2] - best_case[-1][1]) - node_data["gcl_open"]
                        gcl_open = node_data["gcl_offset"]
                        gcl_close = node_data["gcl_offset"]+node_data["gcl_open"]
                        if exceeding > 0:
                            # end of the window is too late, so we can max have an end at latest gate open
                            best_case.append((node_name, gcl_open, gcl_close, best_case[-1][3]+d_trans_bc, best_case[-1][4]+d_trans_bc+exceeding))
                        else:
                            # delay is increased by transmission only
                            best_case.append((node_name, gcl_open, gcl_close, best_case[-1][3]+d_trans_bc, best_case[-1][4]+d_trans_bc))

                        d_gate = node_data["gcl_cycle"]-node_data["gcl_open"]+d_trans+(d_interference/max(1,len(interfering_streams)))
                        d_forward = d_gate+d_dwell#+d_trans+d_blck+d_interference
                        worst_case.append((node_name, gcl_open, gcl_close, worst_case[-1][3]+d_forward, worst_case[-1][4]+d_forward, node_data["gcl_cycle"]))
                        #worst_case.append((node_name, gcl_open, gcl_close, worst_case[-1][3]+d_gate+d_dwell, worst_case[-1][4]+d_gate+d_dwell, node_data["gcl_cycle"]))

                        
                        
                        
                # SP and FP
                else:
                    if is_synchronized and best_case[-1][1] != -1:
                        # we only want to cover synchronized SP and FP after a TAS window, Sp and FP after Sp and FP are in the else branch
                        best_case.append((node_name, best_case[-1][1]+d_trans_bc, best_case[-1][2]+d_trans_bc, best_case[-1][3]+d_trans_bc, best_case[-1][4]+d_trans_bc))
                        worst_case.append((node_name, worst_case[-1][1]+d_dwell+d_interference, worst_case[-1][2]+d_dwell+d_interference, worst_case[-1][3]+d_dwell+d_interference, worst_case[-1][4]+d_dwell+d_interference, worst_case[-2][5]))
                        
                    else:
                        # -1 indicates, that there was an unsync transmission and this node did not put restrictions on the transmission windo --> for next tas node: behave as if unsynchronized
                        best_case.append((node_name, -1, worst_case[-2][5]-(d_trans_wc*3), best_case[-1][3]+d_trans_bc, best_case[-1][4]+d_trans_bc))
                        worst_case.append((node_name, -1, worst_case[-2][5]-(d_trans_wc*3), worst_case[-1][3]+d_dwell+d_interference, worst_case[-1][4]+d_dwell+d_interference, worst_case[-2][5]))

                    
            # if the end of the forwarding window moved before the beginning, we set the window size to 0
            if best_case[-1][2] < best_case[-1][1]:
                best_case[-1] = (best_case[-1][0], best_case[-1][1], best_case[-1][1], best_case[-1][3], best_case[-1][4])
            #if best_case[-1][4] < best_case[-1][3]:
            #    best_case[-1] = (best_case[-1][0], best_case[-1][1], best_case[-1][2], best_case[-1][3], best_case[-1][3])
            if "talker" in node_name or "listener" in node_name:
                best_case[-1] = (best_case[-1][0], best_case[-1][1], best_case[-1][2], best_case[-2][3], best_case[-2][4])
                worst_case[-1] = (worst_case[-1][0], worst_case[-1][1], worst_case[-1][2], worst_case[-2][3], worst_case[-2][4], worst_case[-1][5])

            if port_statistics is not None:
                #port_statistics.best_case = min(best_case[-1][3], best_case[-1][4])-min(best_case[-2][3], best_case[-2][4])
                #port_statistics.worst_case = max(worst_case[-1][3], worst_case[-1][4])-max(worst_case[-2][3], worst_case[-2][4])
                port_statistics.best_case = min(best_case[-1][3], best_case[-1][4])#-min(best_case[-2][3], best_case[-2][4])
                port_statistics.worst_case = max(worst_case[-1][3], worst_case[-1][4])#-max(worst_case[-2][3], worst_case[-2][4])

        debug("BC: ", min(best_case[-2][3], best_case[-2][4]))
        debug("WC: ", max(worst_case[-2][3], worst_case[-2][4]))
        stream.saved_multiplications = multiplication
        return best_case, worst_case, min(best_case[-2][3], best_case[-2][4]), max(worst_case[-2][3], worst_case[-2][4])

    def calculate_delays(self, streams: List[str] = None):
        """
        @param streams Name of the streams for which the best case should be calculated.
        Note: all streams that exist on the topology should be calculated
        """
        for stream in self.streams:
            if streams is not None and len([s for s in streams if s == stream.name]) == 0:
                continue

            self.calculate_delays_for_stream(stream)

    def get_resource_utilization_for_stream(self, stream: Stream):
        debug(f'Calculating resource utilization for stream {stream.name}')

        path = self.stream_paths[stream.name]
        stream_statistics = self.stream_statistics[stream.name]
        stream_statistics.clear_resource_utilization()

        all_nodes = self.topology.G.nodes(data=True)
        all_edges = self.topology.G.edges(data=True)
                
        factor = 1
        occupancies = []
        for index, node_name in enumerate(path):
            node_data = all_nodes[node_name]

            if not is_tx_port(node_name, None, path):
                continue

            debug(f"Calculating node {node_name}")
            port_statistics = stream_statistics.get_port_statistics(node_name)
            edge = self.topology.G.get_edge_data(node_name, path[index+1])

            interfering_streams = self.get_interfering_streams(stream, node_name)
            debug(f'Interfering streams: {", ".join([stream.name for stream in interfering_streams])}')

            interfering_streams_delays = [self.get_stream_transmission_duration(stream, edge["link_speed"], node_name) + edge["transmission_jitter"] for stream in interfering_streams]
            debug(f'Interfering stream delays1: {interfering_streams_delays}')
            try:
                factor *= max(1,stream.saved_multiplications[index])
            except:
                factor *= 1

            if node_data["gcl"]:
                window_size = int(node_data["gcl_open"])
            else:
                window_size = stream.cycletime
            # TODO: why do we add framesize to the delays (also, do we need to add layer 1 overhead)?
            debug("own delay:", (self.get_stream_transmission_duration(stream, edge["link_speed"], node_name)*factor), edge["link_speed"])
            occupancy = sum(interfering_streams_delays) + (self.get_stream_transmission_duration(stream, edge["link_speed"], node_name)*factor)
            debug(f'occupancy: {occupancy}')
            debug(f'window_size: {window_size}')
            occupancies.append(occupancy / window_size)
            port_statistics.resource_utilization = occupancy / window_size
        return occupancies

    def get_resource_utilization(self, streams: List[str] = None):
        """
        @param streams Name of the streams for which the resource utilization should be calculated
        """
        for stream in self.streams:
            self.calculate_delays_for_stream(stream)

        for stream in self.streams:
            if streams is not None and len([s for s in streams if s == stream.name]) == 0:
                continue
            occupancies = self.get_resource_utilization_for_stream(stream)
            return max(occupancies)

    def export_json(self, path: str):
        json_dict = {}

        json_dict['topologyName'] = self.topology.name
        json_dict['streams'] = []

        for stream in self.streams:
            stream_statistics = self.stream_statistics[stream.name]
            stream_dict = {}

            stream_dict['name'] = stream.name
            stream_dict['summarizedBestCaseDelay'] = stream_statistics.get_summarized_best_case()
            stream_dict['summarizedWorstCaseDelay'] = stream_statistics.get_summarized_worst_case()
            stream_dict['delaysPerPort'] = []

            for port_statistics in stream_statistics.delays_per_port:
                port_dict = {}
                port_dict['node'] = port_statistics.node_name
                port_dict['port'] = port_statistics.port_name
                port_dict['direction'] = port_statistics.direction
                port_dict['bestCaseDelay'] = port_statistics.best_case
                port_dict['worstCaseDelay'] = port_statistics.worst_case

                if port_statistics.direction == 'tx':
                    port_dict['resourceUtilization'] = round(port_statistics.resource_utilization, 4)

                stream_dict["delaysPerPort"].append(port_dict)

            json_dict["streams"].append(stream_dict)

        try:
            with open(path, 'w') as f:
                json.dump(json_dict, f, indent=4)
        except IOError as e:
            print(f'Error writing result to file: {e.strerror}')
            return False
        except BaseException as e:
            print(f'Error writing result to file')
            print(e)
            return False

        return True
