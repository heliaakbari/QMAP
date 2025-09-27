
import random
import os
from qiskit.dagcircuit import DAGCircuit
from qiskit.converters import dag_to_circuit
import matplotlib.pyplot as plt

class Splitter:

    def __init__(self, input_dag):
        self.input_dag = input_dag
        self.rev_dag1 = None
        self.dag2 = None
        self.k = None
        self.layers = list(self.input_dag.layers())

    def initialize_dag(self):
        dag = DAGCircuit()

        for qreg in self.input_dag.qregs.values():
            dag.add_qreg(qreg)

        for creg in self.input_dag.cregs.values():
            dag.add_creg(creg)

        return dag

    def splitDagRandom(self):
        k = random.randint(0, len(self.layers))
        self.k = k
        first_layers = self.layers[:k]
        second_layers = self.layers[k:]
        print(f"Splitting after layer {self.k} (out of {len(self.layers)} layers)")

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

    def splitDagStart(self):
        self.k = 0
        self.rev_dag1 = self.initialize_dag()
        self.dag2 = self.input_dag
        return self.rev_dag1, self.dag2

    def splitDagEnd(self):
        self.k = len(self.layers)
        self.rev_dag1 = self.input_dag.reverse_ops()
        self.dag2 = self.initialize_dag()
        return self.rev_dag1, self.dag2

    def visualizeCircuits(self, fpath="./output/visualize/splitter/", dagName="circuit"):

        circuit1 = dag_to_circuit(self.rev_dag1)
        circuit2 = dag_to_circuit(self.dag2)
        circuitInput = dag_to_circuit(self.input_dag)

        os.makedirs(fpath, exist_ok=True)

        # Prepare matplotlib figure (3 rows, 1 column)
        fig, axes = plt.subplots(1, 3, figsize=(18, 10))  # adjust figsize as needed

        # Draw each circuit on its own subplot
        circuitInput.draw(output="mpl", ax=axes[0])
        axes[0].set_title(f"Input Circuit: {len(self.layers)} layers")

        circuit1.draw(output="mpl", ax=axes[1])
        axes[1].set_title(f"First Circuit (rev_dag1): first {self.k} layers")

        circuit2.draw(output="mpl", ax=axes[2])
        axes[2].set_title(f"Second Circuit (dag2): last {len(self.layers) - self.k} layers")

        # Adjust layout
        plt.tight_layout()

        # Save to file
        save_path = os.path.join(fpath, f"{dagName}.png")
        fig.savefig(save_path, dpi=300)
        plt.close(fig)  # free memory

        print(f"Saved visualization to {save_path}")
