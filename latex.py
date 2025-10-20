import numpy as np
from qiskit import QuantumCircuit
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
non_zero_probs = {k: v for k, v in probs.items() if v > 0.00000000001}

if (len(non_zero_probs)==1):
    print(f"circuit {ans} has one output: {non_zero_probs}")
qc.measure_all()
# Create noisy simulator backend
noise_model = NoiseModel.from_backend(backend)
sim_noise = AerSimulator(noise_model=noise_model)

# Transpile circuit for noisy basis gates
passmanager = generate_preset_pass_manager(
    optimization_level=3, backend=sim_noise
)

circ_tnoise = passmanager.run(qc)

# Run and get counts
result_bit_flip = sim_noise.run(circ_tnoise).result()
counts_bit_flip = result_bit_flip.get_counts(0)

print(counts_bit_flip)

