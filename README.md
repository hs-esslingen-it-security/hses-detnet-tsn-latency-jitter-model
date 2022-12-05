# Analyzing and Modeling the Latency and Jitter Behavior of Mixed Industrial TSN and DetNet Networks
This repository implements the model presented at the [CoNEXT '22]().

## Setup
This application requires Python 3.8 or later.

We recommend using a Python virtual environment to install the dependencies with the correct version.
Create a virtual environment in your current folder using the command `python3 -m venv venv`.

Enter the virtual environment using the command `source ./venv/bin/activate` (Linux, MacOS).

Install the dependencies (preferably in the virtual environment) using the command `pip3 install -r requirements.txt`.
Afterward, install the latency model with `pip install .`.

You're ready to go!


## CoNEXT 2022 Dataset
In the `datasets` folder, we stored the file `dataset_conext2022.pkl` containing all measured values from the CoNEXT evaluation. The according topology per setting will be generated based on the setting name.
With the following command, you can execute the modeling for all settings and print the complete table with measured and predicted values. (cf. Table 5 in our paper)
`python -c "import latency_jitter_model; latency_jitter_model.execute_latency_jitter_model_conext_eval(dataset_path='datasets/dataset_conext2022.pkl')"`

The beginning of the table looks as follows:
```
---------------------------------------------------------------------------------------------------
| Setting | Pred. BC [µs] | Meas. BC [µs] | Meas. WC [µs] | Pred. WC [µs] | Pred. Utilization [%] |
---------------------------------------------------------------------------------------------------
|      S1 |          8.04 |         10.62 |         54.85 |         70.01 |                    10 |
|      S2 |          8.04 |         10.84 |         54.59 |         70.01 |                    10 |
|      S3 |         67.02 |         67.37 |          74.3 |         88.48 |                    66 |
|      S4 |         47.02 |         47.65 |         74.29 |        164.96 |                    66 |
|      S5 |          8.04 |         10.37 |        128.52 |        156.77 |                    66 |
|      S6 |          8.04 |         10.18 |        130.63 |        156.77 |                    66 |
|      S7 |          8.01 |         10.08 |        117.17 |        144.48 |                    40 |
|      S8 |          8.01 |         10.07 |        114.86 |        144.48 |                    40 |
|      S9 |         67.02 |         67.37 |        174.29 |        188.48 |                    66 |
...
...
```


## Generic Examples
In this section we introduce the example to use a generic topology stored in JSON format. Example topology files are stored in the `datasets` folder.
The command `python -c "import latency_jitter_model; latency_jitter_model.execute_latency_jitter_model_examples(scenario='arrival_window', topology_path='datasets/topology1.json')"` results in the following output:

```
----------------------------------------
| port       |  best-case | worst-case |
|            |       [ns] |       [ns] |
----------------------------------------
| node 0-tx  |      4135  |      17511 |
----------------------------------------
| node 1-rx  |      5105  |      18541 |
----------------------------------------
| node 1-tx  |     44165  |      56511 |
----------------------------------------
| node 2-rx  |     45135  |      57541 |
----------------------------------------
| node 2-tx  |     84165  |     114297 |
----------------------------------------
| node 3-rx  |     85135  |     115327 |
----------------------------------------
| node 3-tx  |    124165  |     154297 |
----------------------------------------
```

The table shows the arrival window of stream 1 at each node.
Each row in the table corresponds to the reception time (rx) or transmit time (tx) of a frame at the given node.

## Create own scenarios
It is possible to create custom scenarios.
Just extend the list of scenarios (`ALLOWED_SCENARIOS`) in `execute_latency_jitter_model.py` and handle the new scenario below.
It is also possible to create a custom topology as we did in `topology_templates.py`.

## topology.json documentation
This application can import and export topologies in the JSON format.
In the following, we explain the format of the topology.

```json
{
    // The name of the topology
    "name": "Topology 1",
    // Topology description (optional)
    "description": "An optional description",
    // The forwarding nodes in the topology
    "nodes": [
        {
            // Name of the node
            // Important: don't use dashes (`-`) in the name
            "name": "Node 1",
            // Processing delay in ns (default: 1050 )
            "processingDelay": 1050,
            // Processing jitter in ns (default: 50)
            "processingJitter": 50,
            // Name of the domain (default: omitted = None)
            "syncDomain": "Domain 1",
            // Sync jitter in ns, only used if `syncDomain` is defined (default: 30)
            "syncJitter": 30,
            // Ports of the forwarding node
            "ports": [
                {
                    // Name of the port
                    // Important: don't use dashes (`-`) in the name
                    "name": "Port 1",
                    // Whether to enable frame preemption (default: false)
                    "framePreemption": false,
                    // Express priorities, only used if `framePreemption` is enabled
                    // Array of integers from 0 to 7 (default: [])
                    "expressPriorities": [],
                    // Whether to enable GCL (default: false)
                    "gcl": false,
                    // GCL cycle time in ns, only used if `gcl` is enabled (default: 1000000)
                    "gclCycle": 1000000,
                    // Gate open duration in ns, only used if `gcl` is enabled (default: 10000)
                    "gclOpen": 10000,
                    // Gate open offset in ns (from cyle start), only used if `gcl` is enabled (default: 1000)
                    "gclOffset": 1000,
                    // Priorities allowed during GCL open time, only used if `gcl` is enabled
                    // Array of integers from 0 to 7 (default: priorities 0 - 7)
                    "gclPriorities": [0, 1, 2, 3, 4, 5, 6, 7]
                }
            ]
        }
    ],
    // Connections between the forwarding nodes
    "edges": [
        {
            // First node ([node name, port name])
            "port1": ["Node 1", "Port 2"],
            // Second node ([node name, port name])
            "port2": ["Node 2", "Port 1"],
            // Link speed in Mbit/s (default: 1000)
            "linkSpeed": 1000,
            // Maximum frame size that can be transmitted on the link in bytes (default: 1522)
            "maxFrameSize": 1522,
            // Propagation delay in ns (default: 0)
            "propagationDelay": 0,
            // Default transmission jitter in ns (default: 0)
            "transmissionJitter": 0
        }
    ],
    // Streams flowing in the topology
    "streams": [
        {
            // Name of the stream
            "name": "Stream 1",
            // Cycle time in ns
            "cycleTime": 1000,
            // Offset from cycle start in ns
            "offset": 0,
            // Added to offset to calculate the transmission window
            "transmissionWindow": 0,
            // Frame size in bytes (without preamble, start frame delimiter, and interpacket gap)
            "frameSize": 500,
            // Name of the sender node
            "sender": "Node 1",
            // Name of the receiver node
            "receiver": "Node 2",
            // Priority
            // Integer from 0 to 7 (default: 0)
            "priority": 6
        }
    ]
}
```

## Calculation result documentation
This application exports the calculation result to a JSON file.
In the following, we explain the format of the calculation result.

```json
{
    // Name of the input topology
    "topologyName": "Topology 1",
    // Calculation result for each stream
    "streams": [
        {
            // Name of the stream
            "name": "Stream 1",
            // Summarized best case delay over all nodes in nanoseconds
            "summarizedBestCaseDelay": 10000,
            // Summarized worst case delay over all nodes in nanoseconds
            "summarizedWorstCaseDelay": 20000,
            // Delay caused by each node (at rx, tx) that the stream traverses
            "delaysPerPort": [
                {
                    // Name of the node
                    "node": "Node 1",
                    // Name of the port
                    "port": "Port 1",
                    // Whether the port receives or sends the packets of the stream (`rx` or `tx`)
                    "direction": "tx",
                    // Best case delay of this port in nanoseconds
                    "bestCaseDelay": 500,
                    // Worst case delay of this port in nanoseconds
                    "worstCaseDelay": 1000,
                    // Resource utilization at the egress port
                    // Float from 0 to 1
                    // Only valid if `direction` is `tx`
                    "resourceUtilization": 0.5
                }
            ]
        }
    ]
}
```
