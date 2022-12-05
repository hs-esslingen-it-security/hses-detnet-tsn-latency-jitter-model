import argparse
import json
import pickle
from latency_jitter_model.calculator import Calculator
from latency_jitter_model.topology import Topology
from latency_jitter_model.helpers import print_results


ALLOWED_SCENARIOS = ["arrival_window", "congestion", "inefficient_trans"]


def execute_latency_jitter_model_examples(scenario, topology_path, output_path=None):
    """
    @scenario: Name of the scenario (one from ALLOWED_SCENARIOS)
    @topology_path: Path to the topology json file
    @output_path: Path where statistics json file is writen to (optional)
    """
    if scenario not in ALLOWED_SCENARIOS:
        print(f"please choose one of the following scenarios: '{str(ALLOWED_SCENARIOS)}'")
        exit(1)

    try:
        with open(topology_path) as f:
            topology_dict = json.load(f)
    except IOError: 
        print('Error opening topology file')
        exit(1)
    except json.JSONDecodeError as e:
        print('Error parsing JSON from topology file')
        print(e.msg)
        exit(1)
    except:
        print('Error opening and parsing topology file')
        raise

    topology_instance = Topology.from_json(topology_dict)

    calculator = Calculator(topology=topology_instance, streams=topology_instance.streams)
    calculator.calculate_delays()
    calculator.get_resource_utilization()

    if output_path is not None:
        res = calculator.export_json(output_path)
        if res:
            print(f'Successfully wrote calculation result to {output_path}')

    print_results(scenario, topology_instance, calculator)


def execute_latency_jitter_model_conext_eval(dataset_path):
    """
    @dataset_path: Path to the dataset pkl file
    """
    try:
        with open(dataset_path, 'rb') as f:
            dataset = pickle.load(f)
    except IOError: 
        print('Error opening dataset file')
        exit(1)
    except json.JSONDecodeError as e:
        print('Error parsing JSON from dataset file')
        print(e.msg)
        exit(1)
    except:
        print('Error opening and parsing dataset file')
        raise

    errors = []

    print("---------------------------------------------------------------------------------------------------")
    print("| {!s} | {!s} | {!s} | {!s} | {!s} | {!s} |".format(str("Setting").rjust(7), str("Pred. BC [µs]").rjust(13), \
                                                               str("Meas. BC [µs]").rjust(13), str("Meas. WC [µs]").rjust(13), \
                                                               str("Pred. WC [µs]").rjust(13), str("Pred. Utilization [%]").rjust(21)))
    print("---------------------------------------------------------------------------------------------------")

    for ds in dataset:
        topology_instance = Topology(ds["setting"])
        topology_instance.from_toponame(ds["file"])

        calculator = Calculator(topology=topology_instance, streams=topology_instance.streams)

        calculator.calculate_delays()
        calculator.get_resource_utilization()
        stream_statistics = calculator.stream_statistics
        
        c_bc = 0
        c_wc = 0
        c_utilization = 0
        for port_statistics in stream_statistics['Stream 1'].delays_per_port:
            c_bc = port_statistics.best_case
            c_wc = port_statistics.worst_case
            if port_statistics.direction != 'tx' or port_statistics.port_name == None:
                # Only tx ports are valid
                continue
            c_utilization = c_utilization if c_utilization >= round(port_statistics.resource_utilization * 100) \
                                            else round(port_statistics.resource_utilization * 100)
        
        if (c_bc/1000 > ds["mmin"] or c_wc/1000 < ds["mmax"]) and (c_utilization < 100):
            errors.append([ds, c_bc/1000, c_wc/1000, c_utilization])

        print("| {!s} | {!s} | {!s} | {!s} | {!s} | {!s} |".format(str(ds["setting"]).rjust(7), \
                                                                   str(round(c_bc/1000, 2)).rjust(13), \
                                                                   str(round(ds["mmin"], 2)).rjust(13), \
                                                                   str(round(ds["mmax"], 2)).rjust(13), \
                                                                   str(round(c_wc/1000, 2)).rjust(13), \
                                                                   str(round(c_utilization, 2)).rjust(21)))

    print("---------------------------------------------------------------------------------------------------")
    print()
    if len(errors) != 0:
        print(f"Not all predictions allign with the measurements. Following '{len(errors)}' Errors found:")
        for err in errors:
            print(err)
    else:
        print("Success! All measurements are within the predictions!")
