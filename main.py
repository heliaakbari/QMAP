

from test.benchmarks.qft import build_model_circuit
from qiskit import QuantumRegister, QuantumCircuit, transpile
from qiskit.converters import circuit_to_dag, dag_to_circuit
from qiskit.visualization import dag_drawer
from qiskit.dagcircuit import DAGCircuit

import random

qr = QuantumRegister(5)
qc = build_model_circuit(qreg=qr)
qc.draw(output="mpl", filename='qc.png')
qc_t = transpile(qc)
qc_t.draw(output="mpl", filename='qc_t.png')
print(qc_t.draw("text"))
dag = circuit_to_dag(qc)
layers = list(dag.layers())
k = random.randint(0, len(layers))
first_layers = layers[:k]
second_layers = layers[k:]
print(f"Splitting after layer {k} (out of {len(layers)} layers)")

dag1 = DAGCircuit()
print(dag.cregs.keys())
dag1.add_qreg(dag.qregs['q0'])

dag2 = DAGCircuit()
dag2.add_qreg(dag.qregs['q0'])


# Add layers to each
for layer in first_layers:
    dag1.compose(layer["graph"], inplace=True)

for layer in second_layers:
    dag2.compose(layer["graph"], inplace=True)

qc1 = dag_to_circuit(dag1)
qc2 = dag_to_circuit(dag2)

print("First subcircuit:")
print(qc1.draw("text"))

print("Second subcircuit:")
print(qc2.draw("text"))


#dag_drawer(dag=layers[5]["graph"], filename="dag_layer.png",)

# qr=QuantumRegister(2)
# qc=QuantumCircuit(qr)
# qc.cx(qr[1],qr[0])
# qc= transpile(qc, coupling_map=[[0,1]])
# qc.draw(output="mpl", filename='qc.png')

