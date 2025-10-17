from test.benchmarks.qft import build_model_circuit
from test.benchmarks.ripple_adder import build_ripple_adder_circuit
from qiskit import QuantumRegister, QuantumCircuit
from qiskit.converters import circuit_to_dag, dag_to_circuit
import numpy as np
from GreedyE import NoiseAdaptiveLayout
from qiskit.transpiler.passes.layout.full_ancilla_allocation import FullAncillaAllocation
from qiskit.transpiler.passes.layout.enlarge_with_ancilla import EnlargeWithAncilla
from qiskit.transpiler.passes.layout.apply_layout import ApplyLayout
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2, FakeCasablancaV2, FakeMelbourneV2
from qiskit.transpiler.passes import Unroll3qOrMore
from qiskit.visualization import plot_error_map
from SplitCircuit import Splitter
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
from qiskit.transpiler.passes import SabreLayout, HASwap, SabreSwap, GreedyLayout
from qiskit.transpiler import PassManager
from utilities import circuit_error_rate, choose_benchmark, log_event, circuit_two_qubit_error_rate
from qiskit.transpiler.passes import (
    Collect2qBlocks,
    ConsolidateBlocks,
    UnitarySynthesis,
)
import matplotlib.pyplot as plt
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
backend = service.backend("ibm_torino")

print(
    f"Name: {backend.name}\n"
    f"Version: {backend.version}\n"
    f"No. of qubits: {backend.num_qubits}\n"
    f"basis gates: {backend.basis_gates}"
)

i, j = map(int, input().split())


qc, name = choose_benchmark(choice=i)
num_qubits = qc.num_qubits
figure = plot_error_map(backend)
figure.savefig(fname='./processor.png')

log_event("")
log_event(f"circuit: {name}")
log_event(f"gates: {qc.size()}")
log_event(f"depth: {qc.depth(lambda x: x.operation.num_qubits == 2)}")
log_event(f"backend: {backend.backend_name}")

ha_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)

greedy_layout_trials = PassManager(
    [
        GreedyLayout(seed=42,layout_trials=20, coupling_map=backend,max_iterations=15, k=10, skip_routing=False)
    ]
)

greedy_layout_routing = PassManager(
    [
        GreedyLayout(seed=42, coupling_map=backend, routing_pass=HASwap(seed=42, coupling_map=backend.target, fake_run=True, heuristic="decay", trials=10),max_iterations=5, k=20, skip_routing=True, numsplit=j)
    ]
)

ha_swap = PassManager(
    [
        FullAncillaAllocation(backend.target),
        EnlargeWithAncilla(),
        ApplyLayout(),
        HASwap(seed=42,coupling_map=backend.target, heuristic="decay", trials=10, fake_run=False),
    ]
)

sabre_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)

sabre_layout_routing = PassManager(
    [
        SabreLayout(seed=42 ,coupling_map=backend.target,max_iterations=5, skip_routing=True, routing_pass=SabreSwap(seed=42, coupling_map=backend.target, fake_run=True, heuristic="decay", trials=10))
    ]
)

sabre_layout_trial = PassManager(
    [
        SabreLayout(seed=42,layout_trials=20, coupling_map=backend.target,max_iterations=15, skip_routing=True)
    ]
)

sabre_swap = PassManager(
    [
        FullAncillaAllocation(backend.target),
        EnlargeWithAncilla(),
        ApplyLayout(),
        SabreSwap(seed=42,coupling_map=backend.target, heuristic="decay", trials=10, fake_run=False),
    ]
)
# Add pre-layout stage to run extra logical optimization
ha_manager.layout = greedy_layout_routing
ha_manager.routing = ha_swap
# Add pre-layout stage to run extra logical optimization
sabre_manager.layout = sabre_layout_routing
sabre_manager.routing = sabre_swap

import time
from qiskit_ibm_runtime import EstimatorOptions
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit.quantum_info import SparsePauliOp


# Transpile the circuit with each pass manager and measure the time
t0 = time.time()
tqc_1 = sabre_manager.run(qc)
t1 = time.time() - t0

t0 = time.time()
tqc_ha_1 = ha_manager.run(qc)
tha_1 = time.time() - t0

# Obtain the depths and the total number of gates (circuit size)
depth_1 = tqc_1.depth(lambda x: x.operation.num_qubits == 2)
depth_ha_1 = tqc_ha_1.depth(lambda x: x.operation.num_qubits == 2)

size_1 = tqc_1.size()
size_ha_1 = tqc_ha_1.size()

err_1 = circuit_two_qubit_error_rate(tqc_1, backend)
err_ha_1 = circuit_two_qubit_error_rate(tqc_ha_1, backend)
print(f"Estimated sabre circuit fidelity: {err_1:.4f}")
print(f"Estimated HA circuit fidelity: {err_ha_1:.4f}")
#operators_list_1 = [op.apply_layout(tqc_1.layout) for op in operators]
#operators_list_ha_1 = [op.apply_layout(tqc_ha_1.layout) for op in operators]

# Print results
print(f"Pass manager 1 (4,20,20)    : Depth {depth_1}, Size {size_1}, Time {t1:.4f} s")
print(f"pmha_1 (4,20,20)            : Depth {depth_ha_1}, Size {size_ha_1}, Time {tha_1:.4f} s")
log_event(f"Sabre            : Fidelity {err_1}, Depth {depth_1}, Size {size_1}, Time {t1:.4f} s")
log_event(f"HA               : Fidelity {err_ha_1}, Depth {depth_ha_1}, Size {size_ha_1}, Time {tha_1:.4f} s")


# options = EstimatorOptions()
# options.resilience_level = 1
# options.dynamical_decoupling.enable = True
# options.dynamical_decoupling.sequence_type = "XY4"

# Create an Estimator object
# estimator = Estimator(backend, options=options)


# # Submit the circuit to Estimator
# job_1 = estimator.run([(tqc_1, operators_list_1)])
# job_1_id = job_1.job_id()
# print(job_1_id)

# job_ha_1 = estimator.run([(tqc_ha_1, operators_list_ha_1)])
# job_ha_1_id = job_ha_1.job_id()
# print(job_ha_1_id)


# # Run the jobs
# #result_1 = job_1.result()[0]
# print("Job 1 done")

# #result_ha_1 = job_ha_1.result()[0]
# print("Job ha_1 done")

#data = list(range(1, len(operators) + 1))  # Distance between the Z operators

# Normalize and process expectation values for each result
#values_1 = [v / result_1.data.evs[0] for v in result_1.data.evs]
#values_ha_1 = [v / result_ha_1.data.evs[0] for v in result_ha_1.data.evs]

#plt.plot(data, values_1, marker="o", label="pm_1 (4,20,20)")
#plt.plot(data, values_ha_1, marker="o", linestyle="--", label="pmha_1 (4,20,20)")

# plt.xlabel("Distance between qubits $i$")
# plt.ylabel(r"$\langle Z_i Z_0 \rangle / \langle Z_1 Z_0 \rangle $")
# plt.legend()
# plt.show()
