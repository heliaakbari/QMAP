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
)

qc, ans = choose_benchmark()
print(ans)
# Draw the circuit
#print(qc.draw(output="latex_source"))
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
