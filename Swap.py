# Description: This script creates a custom Qiskit backend with a specific
# topology and basis gates, adds a SWAP gate to a circuit, and then
# visualizes the circuit, saving it as a PNG file.

# Ensure necessary libraries are installed:
# pip install qiskit matplotlib pylatexenc

import qiskit
from qiskit.compiler import transpile
from qiskit.providers.fake_provider import GenericBackendV2
import matplotlib.pyplot as plt

# 1. Define the properties for the custom backend
num_qubits = 3

# Heron R2 processors typically use ['id', 'rz', 'sx', 'x', 'ecr'].
# The user requested 'cx', so we define the basis gates accordingly.
# We also include 'swap' as it will be used in the circuit.

# Define a linear connectivity for the 3 qubits: Q0 <-> Q1 <-> Q2
coupling_map = [[0, 1], [1, 0], [1, 2], [2, 1]]

print(f"Defining a generic backend with {num_qubits} qubits...")
print(f"Coupling Map (Connectivity): {coupling_map}\n")

# Create a generic backend instance with the specified properties
# This simulates a real quantum device's constraints
backend = GenericBackendV2(
    num_qubits=num_qubits,
    basis_gates=["cz", "id", "rx", "rz", "rzz", "sx", "x"],
    coupling_map=coupling_map
)

# 2. Create the Quantum Circuit
print("Creating an initial quantum circuit with 3 qubits...")
# Initialize a quantum circuit with 3 quantum bits and 3 classical bits
circuit = qiskit.QuantumCircuit(3, 3)

# Add a SWAP gate between qubit 0 and qubit 1
print("Adding a SWAP gate between qubit 0 and qubit 1...")
circuit.swap(0, 1)
circuit.swap(1,2)

# It's good practice to add measurements to see the outcome if the
# circuit were to be run.
circuit.measure([0, 1, 2], [0, 1, 2])

print("\nInitial Circuit:")
print(circuit)

# 3. Transpile the circuit
print("\nTranspiling the circuit for the backend's basis gates and connectivity...")
transpiled_circuit = transpile(circuit, backend,optimization_level=0)

print("\nTranspiled Circuit:")
print(transpiled_circuit)

# 4. Visualize the transpiled circuit and save it to a file
output_filename = 'transpiled_swap_circuit.png'
print(f"\nVisualizing the transpiled circuit and saving to '{output_filename}'...")

try:
    # Use the 'mpl' drawer for a high-quality image
    fig = transpiled_circuit.draw(output='mpl', style='iqp')
    # Save the figure to a PNG file
    fig.savefig(output_filename, bbox_inches='tight')
    plt.close(fig) # Close the figure to free up memory
    print(f"Successfully saved the circuit diagram to '{output_filename}'.")

except Exception as e:
    print(f"\nAn error occurred during visualization: {e}")
    print("Please ensure you have 'matplotlib' and 'pylatexenc' installed.")
    print("You can install them using: pip install matplotlib pylatexenc")

