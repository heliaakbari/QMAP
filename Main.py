from test.benchmarks.qft import build_model_circuit
from test.benchmarks.ripple_adder import build_ripple_adder_circuit
from qiskit import QuantumRegister, QuantumCircuit
from qiskit.converters import circuit_to_dag
from GreedyE import NoiseAdaptiveLayout
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2
from qiskit.transpiler.passes import Unroll3qOrMore
from qiskit.visualization import plot_error_map
from SplitCircuit import Splitter


qr = QuantumRegister(5)
qc = build_ripple_adder_circuit(3)

dag = circuit_to_dag(qc)

UN = Unroll3qOrMore()
dag = UN.run(dag)

SP = Splitter(dag)
rev_dag1 , dag2 = SP.splitDagRandom()
SP.visualizeCircuits(dagName="test")

backend = FakeGuadalupeV2()
figure = plot_error_map(backend)
figure.savefig(fname='./processor.png')

NL = NoiseAdaptiveLayout(backend=backend)
NL.run(rev_dag1, dag2)
layout = NL.property_set["layout"]
NL.visualize_initial_mapping(qc)

