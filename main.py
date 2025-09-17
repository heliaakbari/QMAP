

from test.benchmarks.qft import build_model_circuit
from test.benchmarks.ripple_adder import build_ripple_adder_circuit
from qiskit import QuantumRegister, QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.visualization import dag_drawer , plot_circuit_layout
from qiskit.dagcircuit import DAGCircuit
from GreedyE import NoiseAdaptiveLayout
import random
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
from qiskit.transpiler.passes import Unroll3qOrMore

qr = QuantumRegister(5)
qc = build_ripple_adder_circuit(3)
qc.draw(output="mpl", filename='c_qc.png')
UN = Unroll3qOrMore()
qc.draw(output="mpl", filename='qc.png')
print(qc.draw("text"))

dag = circuit_to_dag(qc)
dag = UN.run(dag)
layers = list(dag.layers())
k = random.randint(0, len(layers))
first_layers = layers[:k]
second_layers = layers[k:]
print(f"Splitting after layer {k} (out of {len(layers)} layers)")

dag1 = DAGCircuit()
dag2 = DAGCircuit()

for qreg in dag.qregs.values():
    dag1.add_qreg(qreg)
    dag2.add_qreg(qreg)

for creg in dag.cregs.values():
    dag1.add_creg(creg)
    dag2.add_creg(creg)



# Add layers to each
for layer in first_layers:
    dag1.compose(layer["graph"], inplace=True)

rev_dag1 = dag1.reverse_ops()
qc1 = dag_to_circuit(dag1)

for layer in second_layers:
    dag2.compose(layer["graph"], inplace=True)

rev_qc1 = dag_to_circuit(rev_dag1)
qc2 = dag_to_circuit(dag2)

print("reverse dag first subcircuit:")
print(rev_qc1.draw("text"))

print("reverse circuit first subcircuit:")
print(qc1.reverse_ops().draw("text"))

print("Second subcircuit:")
print(qc2.draw("text"))

backend = FakeGuadalupeV2()

NL = NoiseAdaptiveLayout(backend_prop=backend.properties(),coupling_map=backend.coupling_map)
NL.run(rev_dag1, dag2)
layout = NL.property_set["layout"]
print(layout)
