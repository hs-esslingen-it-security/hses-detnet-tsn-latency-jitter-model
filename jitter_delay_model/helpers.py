from typing import Dict, Literal, List

from jitter_delay_model.path_helpers import is_rx_port

DEBUG = False

class TopologyParsingError(Exception):
    pass

Priority = Literal[0, 1, 2, 3, 4, 5, 6, 7]
"""Corresponds to PCP field in the VLAN tag"""

ExpressPriorities = List[Priority]
GclPriorities = List[Priority]
"""List of priorities that can preempt other frames with priorities that are not part of the express group"""

StreamDelay = Dict[str, int]
"""Delay caused by each node on the path of a stream.

The key corresponds to the name of a node, and the value is the latency caused by that node in nanoseconds.
Rx and tx of a node are separated using the suffix "-rx" and "-tx".
Rx includes the processing delay, tx all other delays caused by queueing and transmission of a frame.
"""

class PortStatistics:
    def __init__(self, node_name: str, port_name: str, direction: Literal['rx', 'tx'], best_case: int = 0, worst_case: int = 0, resource_utilization: float = 0) -> None:
        self.node_name: str = node_name
        self.port_name: str = port_name
        self.direction: Literal['rx', 'tx'] = direction
        self.best_case: int = best_case
        self.worst_case: int = worst_case
        self.resource_utilization: float = resource_utilization
        """Resource utilization is only valid for tx ports"""

    def clear(self):
        self.best_case = 0
        self.worst_case = 0
        self.resource_utilization = 0

class StreamStatistics:
    def __init__(self, stream_name: str, path: List[str], all_node_data) -> None:
        self.stream_name: str = stream_name
        self.delays_per_port: List[PortStatistics] = []

        for index, node_name in enumerate(path):
            if index == 0:
                continue
            if index == len(path)-1:
                break
            if is_rx_port(node_name, None, path):
                continue

            node_data = all_node_data[node_name]

            if node_data["forwarding_node"]:
                direction = 'rx'
            else:
                direction = 'tx'

            split = node_name.split('-')
            self.delays_per_port.append(PortStatistics(
                node_name=split[0],
                port_name=split[1] if len(split) > 1 else None,
                direction=direction
            ))

    def clear(self):
        for statistics in self.delays_per_port:
            statistics.clear()

    def clear_best_case(self):
        for statistics in self.delays_per_port:
            statistics.best_case = 0

    def clear_worst_case(self):
        for statistics in self.delays_per_port:
            statistics.worst_case = 0

    def clear_resource_utilization(self):
        for statistics in self.delays_per_port:
            statistics.resource_utilization = 0

    def get_port_statistics(self, node_name: str, port_name: str = None) -> PortStatistics:
        """Returns statistics for the given port.

        If `node_name` and `port_name` are concatenated using "-" in one string, set `port_name` to None and only use `node_name`
        """
        if port_name is None:
            split = node_name.split('-')
            node_name = split[0]
            port_name = split[1] if len(split) > 1 else None

        return [d for d in self.delays_per_port if d.node_name == node_name and (port_name is None or d.port_name == port_name)][0]

    def get_summarized_best_case(self, stop_at_node: str = None) -> int:
        """Calculates and returns the best case sum of the delays caused by each node in nanoseconds
        @param stop_at_node Only calculates the sum until (including) the given node name (must include the -tx/-rx)
        """
        if stop_at_node is None:
            delays = [statistics.best_case for statistics in self.delays_per_port]
        else:
            delays = []
            for statistics in self.delays_per_port:
                delays.append(statistics.best_case)
                if stop_at_node == f'{statistics.node_name}-{statistics.port_name}-{statistics.direction}':
                    break

        return sum(delays)

    def get_summarized_worst_case(self, stop_at_node: str = None) -> int:
        """Calculates and returns the worst case sum of the delays caused by each node in nanoseconds
        @param stop_at_node Only calculates the sum until (including) the given node name (must include the -tx/-rx)
        """
        if stop_at_node is None:
            delays = [statistics.worst_case for statistics in self.delays_per_port]
        else:
            delays = []
            for statistics in self.delays_per_port:
                delays.append(statistics.worst_case)
                if stop_at_node == f'{statistics.node_name}-{statistics.port_name}-{statistics.direction}':
                    break

        return sum(delays)

    # def add_best_case(self, node_name: str, port_name: str, delay: int):
    #     """Adds the best case for the given node and port.

    #     If `node_name` and `port_name` are concatenated using "-" in one string, set `port_name` to None and only use `node_name`
    #     """

    #     port_statistics = self.get_port_statistics(node_name, port_name)
    #     port_statistics.best_case = delay

    # def add_worst_case(self, node_name: str, port_name: str, delay: int):
    #     """Adds the worst case for the given node and port.

    #     If `node_name` and `port_name` are concatenated using "-" in one string, set `port_name` to None and only use `node_name`
    #     """

    #     port_statistics = self.get_port_statistics(node_name, port_name)
    #     port_statistics.worst_case = delay

    # def add_resource_utilization(self, node_name: str, port_name: str, utilization: float):
    #     """Adds the resource utilization for the given node and port.

    #     If `node_name` and `port_name` are concatenated using "-" in one string, set `port_name` to None and only use `node_name`
    #     """

    #     port_statistics = self.get_port_statistics(node_name, port_name)
    #     port_statistics.resource_utilization = utilization

def debug(*text):
    if DEBUG:
        print(*text)

def get_transmission_duration(framesize: int, link_speed: int) -> int:
    """Calculates transmission duration of the stream using given frame size and given link speed

    @framesize Frame size in bytes (must include L1 overhead)
    @link_speed Link speed in Mbit/s

    @returns Transmission duration in bytes
    """
    return ((framesize) / (link_speed / 8 * 1000000)) * 1000000000

def get_summarized_delay(stream_delay: StreamDelay, stop_at_node: str = None) -> int:
    """Calculates and returns the sum of the delays caused by each node in nanoseconds
    @param stop_at_node Only calculates the sum until (including) the given node name (must include the -tx/-rx)

    TODO: deprecated
    """
    if stop_at_node is None:
        delays = [delay for node_name, delay in stream_delay.items() if "offset" not in node_name]
    else:
        delays = []
        for node_name, delay in stream_delay.items():
            delays.append(delay)
            if stop_at_node == node_name:
                break

    return sum(delays)


def print_results(scenario, topology_instance, calculator):
    stream_statistics = calculator.stream_statistics
    if scenario == "arrival_window":
        print()
        print()
        print(f"Arrival Window Calculation: (Topology {topology_instance.name})")
        # sorted_list = [elem for elem in s1.best_case] #sorted(s1.worst_case, key=lambda k: s1.worst_case[k], reverse=True)
        print("----------------------------------------")
        print("| {!s} |  {!s} | {!s} |".format(str("port").ljust(10), str("best-case"), str("worst-case")))
        print("| {!s} |       {!s} |       {!s} |".format(str("").ljust(10), str("[ns]"), str("[ns]")))
        c_bc = 0
        c_wc = 0
        for port_statistics in stream_statistics['Stream 1'].delays_per_port:
            c_bc += port_statistics.best_case
            c_wc += port_statistics.worst_case
            print("----------------------------------------")
            print("| {!s} |   {!s}  |    {!s} |".format(f'{port_statistics.node_name}-{port_statistics.direction}'.ljust(10), str(int(c_bc)).rjust(7), str(int(c_wc)).rjust(7)))
        print("----------------------------------------")
        print()
        print()

    elif scenario == "congestion":
        print()
        print()
        print(f"Congestion Identification: (Topology {topology_instance.name})")
        # sorted_list = sorted(s1.worst_case, key=lambda k: s1.worst_case[k], reverse=True)
        print("-----------------------------------")
        print("|   {!s}   | {!s}  |".format(str("port").ljust(10), str("occupancy [%]").rjust(10)))


        for port_statistics in stream_statistics['Stream 1'].delays_per_port:
            if port_statistics.direction != 'tx' or port_statistics.port_name == None:
                # Only tx ports are valid
                continue

            print("-----------------------------------")                    
            print("|   {!s}   |   {!s}   |".format(f'{port_statistics.node_name}-{port_statistics.direction}'.ljust(10), str(round(port_statistics.resource_utilization * 100)).rjust(10)))
        print("-----------------------------------")
        print()
        print()


    elif scenario == "inefficient_trans":
        print()
        print()
        print(f"Inefficient Transitions: (Topology {topology_instance.name})")
        sorted_list = sorted(stream_statistics['Stream 1'].delays_per_port, key=lambda statistics: statistics.worst_case, reverse=True)
        print("-----------------------------------")
        print("|   {!s}   |   {!s}   |".format(str("transition").ljust(10), str("delay [ns]").rjust(10)))
        for elem in sorted_list:
            print("-----------------------------------")
            print("|   {!s}   |   {!s}   |".format(f'{elem.node_name}-{elem.direction}'.ljust(10), str(int(elem.worst_case)).rjust(10)))
        print("-----------------------------------")
        print()
        print()