from qiskit import QuantumCircuit, transpile
from qiskit.visualization import plot_histogram
from qiskit_ibm_runtime import SamplerV2
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
from matplotlib import pyplot as plt

# Get a fake backend from the fake provider
backend = FakeGuadalupeV2()

# Create a simple circuit
circuit = QuantumCircuit(3)
circuit.h(0)
circuit.cx(0, 1)
circuit.cx(0, 2)
circuit.measure_all()

# Draw original circuit
circuit.draw('mpl', style="iqp")
plt.show()

# Transpile and draw
transpiled_circuit = transpile(circuit, backend)
transpiled_circuit.draw('mpl', style="iqp")
plt.show()

# Run sampler
sampler = SamplerV2(backend)
job = sampler.run([transpiled_circuit])
pub_result = job.result()[0]
counts = pub_result.data.meas.get_counts()

# Plot histogram
plot_histogram(counts)
plt.show()


from qiskit.visualization import plot_gate_map

# Plot the FakeManilaV2 device coupling map
plot_gate_map(backend)
plt.show()
