from qiskit import QuantumCircuit
from utilities import choose_benchmark
# Create a Quantum Circuit with 2 qubits and 2 classical bits

qc, ans = choose_benchmark()
# Draw the circuit
print(qc.draw(output="latex_source"))



def splitDagRandom(self):
        self.k = random.randint(0, len(self.layers))
        first_layers = self.layers[:self.k]
        second_layers = self.layers[self.k:]

        dag1 = self.initialize_dag()
        dag2 = self.initialize_dag()

        # Add layers to each
        for layer in first_layers:
            dag1.compose(layer["graph"], inplace=True)

        rev_dag1 = dag1.reverse_ops()

        for layer in second_layers:
            dag2.compose(layer["graph"], inplace=True)

        self.rev_dag1 = rev_dag1
        self.dag2 = dag2
        return self.rev_dag1, self.dag2
