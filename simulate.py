import numpy as np
from utilities import circuit_error_rate
from qiskit import QuantumCircuit
from qiskit.transpiler.passes.layout.apply_layout import ApplyLayout
from qiskit.transpiler.passes.layout.enlarge_with_ancilla import EnlargeWithAncilla
from qiskit.transpiler.passes.layout.full_ancilla_allocation import FullAncillaAllocation
from qiskit.transpiler.passes.layout.greedy_layout import GreedyLayout
from qiskit.transpiler.passes.layout.sabre_layout import SabreLayout
from qiskit.transpiler.passes.routing.ha_swap import HASwap
from qiskit.transpiler.passes.routing.sabre_swap import SabreSwap
from qiskit.transpiler.passmanager import PassManager
from qiskit.quantum_info import Kraus, SuperOp
from qiskit.visualization import plot_histogram
from qiskit.transpiler import generate_preset_pass_manager
from qiskit_aer import AerSimulator
from qiskit import QuantumCircuit
from utilities import choose_benchmark
from qiskit.quantum_info import Statevector
from qiskit_aer.noise import (
    NoiseModel,
    QuantumError,
    ReadoutError,
    depolarizing_error,
    pauli_error,
    thermal_relaxation_error,
)
# Create a Quantum Circuit with 2 qubits and 2 classical bits
from qiskit_ibm_runtime import QiskitRuntimeService
service = QiskitRuntimeService()
backend = service.backend("ibm_torino")

print(
    f"Name: {backend.name}\n"
    f"Version: {backend.version}\n"
    f"No. of qubits: {backend.num_qubits}\n"
    f"basis gates: {backend.basis_gates}"
)

qc, ans = choose_benchmark()
# Draw the circuit
#print(qc.draw(output="latex_source"))


state = Statevector.from_instruction(qc)

# Get all probabilities
probs = state.probabilities_dict()

# Filter out zero probabilities
non_zero_probs = {k: v for k, v in probs.items() if v > 0.000000001}
if (len(non_zero_probs)==1):
    print(f"circuit {ans} has one output: {non_zero_probs}")
else:
    print('more then one')
qc.measure_all()
# Create noisy simulator backend
noise_model = NoiseModel.from_backend(backend)
sim_noise = AerSimulator(noise_model=noise_model)

ha_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
j=3
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

ha_circuit = ha_manager.run(qc)
sabre_circuit = sabre_manager.run(qc)

# Run and get counts
result_bit_flip = sim_noise.run(ha_circuit).result()
ha_result = result_bit_flip.get_counts(ha_circuit)

result_bit_flip = sim_noise.run(sabre_circuit).result()
sabre_result = result_bit_flip.get_counts(sabre_circuit)

ha_sorted_result = dict(sorted(ha_result.items(), key=lambda x: x[1], reverse=True))

sabre_sorted_result = dict(sorted(sabre_result.items(), key=lambda x: x[1], reverse=True))

print(f"ha: {ha_sorted_result}")

print(f"sabre: {sabre_sorted_result}")

ha_esp=circuit_error_rate(backend=backend, circuit=ha_circuit)
sabre_esp=circuit_error_rate(backend=backend, circuit=sabre_circuit)

# Prepare data row
data = {
    "circuit": ans,
    "sabre ESP": sabre_esp,
    "ha ESP": ha_esp,
}

import pandas as pd
import os
# Create a DataFrame
df = pd.DataFrame([data])

# Save to CSV (append if file exists)
csv_file = "simulate/results.csv"
if not os.path.isfile(csv_file):
    df.to_csv(csv_file, index=False)
else:
    df.to_csv(csv_file, mode="a", header=False, index=False)

print(f"\n✅ Results saved to {csv_file}")
