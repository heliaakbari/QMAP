import numpy as np
from qiskit import qasm2, QuantumCircuit
import math
benchmarks=[
    "4gt13_92",
    "4mod5-v1_22",
    "9symml_195",
    "adr4_197",
    "alu-v0_27",
    "co14_215",
    "cycle10_2_110",
    "decod24-v2_43",
    "ising_model_10",
    "ising_model_13",
    "ising_model_16",
    "misex1_241",
    "mod5mils_65",
    "qaoa_n6",
    "qft_10",
    "qft_n13",
    "qft_16",
    "qft_n20",
    "radd_250",
    "rd73_252",
    "rd84_253",
    "sqn_258",
    "square_root_7",
    "sym6_145",
    "sym9_193",
    "z4_268"
]


def circuit_error_rate(circuit, backend):
    props = backend.properties()
    error_probs = []

    for instr, qargs, _ in circuit.data:
        name = instr.name
        qubits = [circuit.find_bit(q).index for q in qargs]

        if name == "measure":
            for q in qubits:
                meas_err = props.qubit_property(q, "readout_error")[0]
                error_probs.append(meas_err)
        else:
            try:
                gate_err = props.gate_error(name, qubits)
                error_probs.append(gate_err)
            except:
                # Gate not found (maybe it's a virtual gate like 'id' or 'u3')
                pass

    # Approximate total error = 1 - product of (1 - p_i)
    fidelity_log  = math.pow(math.e, np.sum([math.log(1 - p) for p in error_probs]))
    return fidelity_log

def circuit_two_qubit_error_rate(circuit, backend):
    props = backend.properties()
    error_probs = []

    for instr, qargs, _ in circuit.data:
        qubits = [circuit.find_bit(q).index for q in qargs]

        # Only consider 2-qubit gates
        if len(qubits) == 2:
            try:
                gate_err = props.gate_error(instr.name, qubits)
                error_probs.append(gate_err)
                #print(instr.name)
            except:
                # Gate not found in backend properties (e.g., virtual or synthesized gate)
                pass

    # If no 2-qubit gates, return perfect fidelity (1.0)
    if not error_probs:
        return 1.0

    # Approximate total 2-qubit fidelity = product of (1 - p_i)
    fidelity = math.exp(np.sum([math.log(1 - p) for p in error_probs]))
    return fidelity


def choose_benchmark(choice=None):
    #for i in benchmarks:
    #    print(f"{benchmarks.index(i)}: {i}")
    if choice:
        ans= choice
    else:
        ans = int(input())
    ans = benchmarks[int(ans)]
    qc = QuantumCircuit.from_qasm_file(f"./benchmark/{ans}.qasm")
    return qc, ans

import re

LOG_FILE = "logs_final.txt"
EXCEL_LOG = "logs_excel_final.txt"

#LOG_FILE = "oncelog.txt"
#EXCEL_LOG = "oncelogs_excel.txt"

# internal buffer for current run
current_run = {}

def log_event(message: str):
    """Write raw log + capture structured values for Excel log."""
    with open(LOG_FILE, "a") as f:
        f.write(f"[] {message}\n")

    # Try to parse structured messages
    parse_for_excel(message)


def parse_for_excel(message: str):
    """Extract info from a log line and store in current_run."""
    global current_run

    msg = message.strip()

    # Generic key: value lines
    if ":" in msg and not msg.startswith(("Sabre", "HA")):
        key, val = msg.split(":", 1)
        current_run[key.strip().lower()] = val.strip()
        return

    # Parse Sabre or HA lines
    if msg.startswith("Sabre") or msg.startswith("HA"):
        algo = "sabre" if msg.startswith("Sabre") else "ha"

        # Extract Fidelity, Depth, Size, Time with regex
        m = re.search(
            r"Fidelity ([\deE\+\-\.]+), Depth (\d+), Size (\d+), Time ([\d\.]+)",
            msg
        )
        if m:
            current_run[f"{algo} fidelity"] = m.group(1)
            current_run[f"{algo} depth"] = m.group(2)
            current_run[f"{algo} size"] = m.group(3)
            current_run[f"{algo} time"] = m.group(4)

        # If HA line → assume run is finished
        if algo == "ha":
            flush_run()


def flush_run():
    """Write current_run to Excel-compatible log (tab separated)."""
    global current_run

    headers = [
        "circuit", "gates", "depth", "backend", "split num", "split at",
        "sabre fidelity", "sabre depth", "sabre size", "sabre time",
        "ha fidelity", "ha depth", "ha size", "ha time"
    ]

    # check if excel log already exists
    try:
        with open(EXCEL_LOG, "r") as f:
            exists = True
    except FileNotFoundError:
        exists = False

    with open(EXCEL_LOG, "a") as f:
        if not exists:
            f.write("\t".join(headers) + "\n")

        row = [current_run.get(h, "") for h in headers]
        f.write("\t".join(row) + "\n")

    # reset for next run
    current_run = {}
