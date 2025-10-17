# This code is part of Qiskit.
#
# (C) Copyright IBM 2017, 2019.
#
# This code is licensed under the Apache License, Version 2.0. You may
# obtain a copy of this license in the LICENSE.txt file in the root directory
# of this source tree or at http://www.apache.org/licenses/LICENSE-2.0.
#
# Any modifications or derivative works of this code must retain this
# copyright notice, and modified files need to carry a notice indicating
# that they have been altered from the originals.

"""Choose a noise-adaptive Layout based on current calibration data for the backend."""

"""
usecase:
NL = NoiseAdaptiveLayout(backend_prop=backend.properties(),coupling_map=backend.coupling_map)
NL.run(rev_dag1, dag2)
layout = NL.property_set["layout"]
"""
import os
import math
from qiskit.visualization import plot_gate_map, plot_circuit_layout
from copy import deepcopy
import rustworkx as rx
from rustworkx.visualization import mpl_draw
import matplotlib.pyplot as plt
from qiskit.dagcircuit import DAGCircuit
from qiskit.providers import BackendV2
from qiskit.transpiler.layout import Layout
from qiskit.transpiler.basepasses import AnalysisPass
from qiskit.transpiler.exceptions import TranspilerError
from collections import defaultdict
from SplitCircuit import Splitter

class NoiseAdaptiveLayout(AnalysisPass):
    """Choose a noise-adaptive Layout based on current calibration data for the backend.

     This pass associates a physical qubit (int) to each virtual qubit
     of the circuit (Qubit), using calibration data.

     The pass implements the qubit mapping method from:
     Noise-Adaptive Compiler Mappings for Noisy Intermediate-Scale Quantum Computers
     Prakash Murali, Jonathan M. Baker, Ali Javadi-Abhari, Frederic T. Chong, Margaret R. Martonosi
     ASPLOS 2019 (arXiv:1901.11054).

    Methods:

     Ordering of edges:
     Map qubits edge-by-edge in the order of decreasing frequency of occurrence in the program dag.

     Initialization:
     If an edge exists with both endpoints unmapped,
     pick the best available hardware cx to execute this edge.
     Iterative step:
     When an edge exists with one endpoint unmapped,
     map that endpoint to a location which allows
     maximum reliability for CNOTs with previously mapped qubits.
     In the end if there are unmapped qubits (which don't
     participate in any CNOT), map them to any available
     hardware qubit.

     Notes:
         even though a `layout` is not strictly a property of the DAG,
         in the transpiler architecture it is best passed around between passes
         by being set in `property_set`.
    """

    def __init__(self, backend:BackendV2, k: int = 3):
        """NoiseAdaptiveLayout initializer.

        Args:
            backend_prop (Union[BackendProperties, Target]): backend properties object
            coupling_map (CouplingMap): Optional. To filter the backend_prop qubits/gates.
                This parameter is ignored if :class:`.Target` is provided in ``backend_prop``.
                That method is preferred.

        Raises:
            TranspilerError: if invalid options
        """
        super().__init__()
        self.backend = backend
        self.k=k
        backend_prop = backend.properties()
        self.target = backend.properties()
        if backend.coupling_map:
            # A backend might have more properties than qubits/gates in the configuration. This is a
            # problem that the Target path should handle differently (by solving that possible
            # inconsistency internally). For the non-target path, this is a possible solution.
            # See https://github.com/Qiskit/qiskit/issues/7677
            backend_prop = deepcopy(backend_prop)
            edge_set = set(backend.coupling_map.graph.edge_list())
            backend_prop.gates = filter(
                lambda ginfo: tuple(ginfo.qubits) in edge_set,
                backend_prop.gates,
            )
            backend_prop.qubits = backend_prop.qubits[: 1 + max(backend.coupling_map.physical_qubits)]
        self.backend_prop = backend_prop

        self.swap_graph = rx.PyDiGraph()
        self.cx_reliability = {}
        self.readout_reliability = {}
        self.hw_qubits = []
        self.gate_list = []
        self.gate_reliability = {}
        self.swap_reliabs = {}

        self.prog_graph = rx.PyGraph()
        self.prog_neighbors = {}
        self.qarg_to_id = {}
        self.program_edges = []

        backend_prop = self.backend_prop
        edge_list = []
        for ginfo in backend_prop.gates:
            if ginfo.gate == "cz" or ginfo.gate == "cx":
                for item in ginfo.parameters:
                    if item.name == "gate_error":
                        g_reliab = 1.0 - item.value
                        break
                    g_reliab = 1.0
                swap_reliab = pow(g_reliab, 3)
                # convert swap reliability to edge weight
                # for the Floyd-Warshall shortest weighted paths algorithm
                swap_cost = -math.log(swap_reliab) if swap_reliab != 0 else math.inf
                edge_list.append((ginfo.qubits[0], ginfo.qubits[1], swap_cost))
                edge_list.append((ginfo.qubits[1], ginfo.qubits[0], swap_cost))
                self.cx_reliability[(ginfo.qubits[0], ginfo.qubits[1])] = g_reliab
                self.gate_list.append((ginfo.qubits[0], ginfo.qubits[1]))
        self.swap_graph.extend_from_weighted_edge_list(edge_list)
        idx = 0
        for q in backend_prop.qubits:
            for nduv in q:
                if nduv.name == "readout_error":
                    self.readout_reliability[idx] = 1.0 - nduv.value
                    self.hw_qubits.append(idx)
            idx += 1
        for edge in self.cx_reliability:
            self.gate_reliability[edge] = (
                self.cx_reliability[edge]
                * self.readout_reliability[edge[0]]
                * self.readout_reliability[edge[1]]
            )

        sorted_edges = sorted(self.gate_reliability.items(), key=lambda x: x[1], reverse=True)

        # for edge, val in sorted_edges:
        #     print(edge, ":", val)

        swap_reliabs_ro = rx.digraph_floyd_warshall_numpy(self.swap_graph, lambda weight: weight)
        for i in range(swap_reliabs_ro.shape[0]):
            self.swap_reliabs[i] = {}
            for j in range(swap_reliabs_ro.shape[1]):
                if (i, j) in self.cx_reliability:
                    self.swap_reliabs[i][j] = self.cx_reliability[(i, j)]
                elif (j, i) in self.cx_reliability:
                    self.swap_reliabs[i][j] = self.cx_reliability[(j, i)]
                else:
                    best_reliab = 0.0
                    for n in self.swap_graph.neighbors(j):
                        if (n, j) in self.cx_reliability:
                            reliab = math.exp(-swap_reliabs_ro[i][n]) * self.cx_reliability[(n, j)]
                        else:
                            reliab = math.exp(-swap_reliabs_ro[i][n]) * self.cx_reliability[(j, n)]
                        if reliab > best_reliab:
                            best_reliab = reliab
                    self.swap_reliabs[i][j] = best_reliab


    def _qarg_to_id(self, qubit):
        """Convert qarg with name and value to an integer id."""
        return self.qarg_to_id[qubit]

    def _create_program_graph(self, dag):
        """Program graph has virtual qubits as nodes.

        Two nodes have an edge if the corresponding virtual qubits
        participate in a 2-qubit gate. The edge is weighted by the
        number of CNOTs between the pair.
        """
        idx = 0
        for q in dag.qubits:
            self.qarg_to_id[q] = idx
            idx += 1
        for layer_index, layer in enumerate(self.dag_only_two_qubit_ops(dag).layers()):
            for gate in layer["graph"].two_qubit_ops():
                qid1 = self._qarg_to_id(gate.qargs[0])
                qid2 = self._qarg_to_id(gate.qargs[1])
                edge = tuple(sorted((qid1, qid2)))  # undirected edge

                # Weight decays as 1 / 2^layer_index
                layer_weight = 1 / (2 ** layer_index)

                # Add weight to existing edge
                self.program_edge_dict[edge] += layer_weight

        return idx



    def _select_next_edge(self, pending_edges, prog2hw):
        """Select the next edge.

        If there is an edge with one endpoint mapped, return it.
        Else return in the first edge
        """
        for edge in pending_edges:
            q1_mapped = edge[0] in prog2hw
            q2_mapped = edge[1] in prog2hw
            assert not (q1_mapped and q2_mapped)
            if q1_mapped or q2_mapped:
                return edge
        return pending_edges[0]

    def _select_best_remaining_cx(self,available_hw_qubits):
        """Select best remaining CNOT in the hardware for the next program edge."""
        candidates = []
        for gate in self.gate_list:
            chk1 = gate[0] in available_hw_qubits
            chk2 = gate[1] in available_hw_qubits
            if chk1 and chk2:
                candidates.append(gate)
        best_reliab = 0
        best_item = None
        for item in candidates:
            if self.gate_reliability[item] > best_reliab:
                best_reliab = self.gate_reliability[item]
                best_item = item
        return best_item

    def _select_best_remaining_qubit(self, prog_qubit, available_hw_qubits, prog2hw):
        """Select the best remaining hardware qubit for the next program qubit."""
        reliab_store = {}
        if prog_qubit not in self.prog_neighbors:
            self.prog_neighbors[prog_qubit] = self.prog_graph.neighbors(prog_qubit)
        for hw_qubit in available_hw_qubits:
            reliab = 1
            for n in self.prog_neighbors[prog_qubit]:
                if n in prog2hw:
                    reliab *= self.swap_reliabs[prog2hw[n]][hw_qubit]
            reliab *= self.readout_reliability[hw_qubit]
            reliab_store[hw_qubit] = reliab
        max_reliab = 0
        best_hw_qubit = None
        for hw_qubit in reliab_store:
            if reliab_store[hw_qubit] > max_reliab:
                max_reliab = reliab_store[hw_qubit]
                best_hw_qubit = hw_qubit
        return best_hw_qubit

    def _score_mapping(self, mapping):
        score = 0
        for (u, v, w) in self.program_edge_list:
            if u in mapping and v in mapping:
                hw_u, hw_v = mapping[u], mapping[v]
                if (hw_u, hw_v) in self.cx_reliability:
                    R = self.cx_reliability[(hw_u, hw_v)]
                elif (hw_v, hw_u) in self.cx_reliability:
                    R = self.cx_reliability[(hw_v, hw_u)]
                else:
                    R = self.swap_reliabs[hw_u][hw_v]
                score += R * w
        return score

    def dag_only_two_qubit_ops(self, dag):
        """Return a new DAGCircuit containing only the 2-qubit gates from the input DAG."""
        new_dag = DAGCircuit()

        for creg in dag.cregs.values():
            new_dag.add_creg(creg)

        for creg in dag.qregs.values():
            new_dag.add_qreg(creg)

        for node in dag.topological_op_nodes():
            if len(node.qargs) == 2:  # keep only 2-qubit operations
                new_dag.apply_operation_back(node.op, qargs=node.qargs, cargs=node.cargs)

        return new_dag

    def run(self, dag, numsplit):

        SP = Splitter(dag)
        dag1 , dag2 = SP.splitDagRandom(numsplit)
        #SP.visualizeCircuits(dagName="test")

        self.available_hw_qubits = []

        self.prog_graph = rx.PyGraph()
        self.prog_neighbors = {}
        self.qarg_to_id = {}
        self.program_edge_dict = defaultdict(float)
        self.program_edge_list = []

        num_qubits = self._create_program_graph(dag1)
        num_qubits = self._create_program_graph(dag2)

        self.program_edge_list = [(u, v, w) for (u, v), w in self.program_edge_dict.items()]
        self.prog_graph.extend_from_weighted_edge_list(self.program_edge_list)

        if num_qubits > len(self.backend_prop.qubits):
            raise TranspilerError("Number of qubits greater than device.")

        # sort by weight, then edge name for determinism (since networkx on python 3.5 returns
        # different order of edges)
        self.program_edges = sorted(
            self.prog_graph.weighted_edge_list(), key=lambda x: [x[2], -x[0], -x[1]], reverse=True
        )
        if not self.program_edges:
            return

        #print(self.program_edges)

        best_hw_edges = sorted(self.gate_reliability.items(), key=lambda x: x[1], reverse=True)[: self.k*2]

        candidate_scores = []

        for hw_edge, _ in best_hw_edges:

            pending_edges = deepcopy(self.program_edges)
            available_hw_qubits = deepcopy(self.hw_qubits)
            prog2hw = {}
            first_edge = pending_edges[0]
            prog2hw[first_edge[0]] = hw_edge[0]
            prog2hw[first_edge[1]] = hw_edge[1]
            available_hw_qubits.remove(hw_edge[0])
            available_hw_qubits.remove(hw_edge[1])

            while pending_edges:
                new_edges = [
                    x
                    for x in pending_edges
                    if not (x[0] in prog2hw and x[1] in prog2hw)
                ]
                pending_edges = new_edges

                if not pending_edges:
                    break

                edge = self._select_next_edge(pending_edges,prog2hw)
                q1_mapped = edge[0] in prog2hw
                q2_mapped = edge[1] in prog2hw
                if (not q1_mapped) and (not q2_mapped):
                    best_hw_edge = self._select_best_remaining_cx(available_hw_qubits)
                    if best_hw_edge is None:
                        raise TranspilerError(
                            "CNOT({}, {}) could not be placed "
                            "in selected device.".format(edge[0], edge[1])
                        )
                    prog2hw[edge[0]] = best_hw_edge[0]
                    prog2hw[edge[1]] = best_hw_edge[1]
                    available_hw_qubits.remove(best_hw_edge[0])
                    available_hw_qubits.remove(best_hw_edge[1])
                elif not q1_mapped:
                    best_hw_qubit = self._select_best_remaining_qubit(edge[0],available_hw_qubits,prog2hw)
                    if best_hw_qubit is None:
                        raise TranspilerError(
                            "CNOT({}, {}) could not be placed in selected device. "
                            "No qubit near qr[{}] available".format(edge[0], edge[1], edge[0])
                        )
                    prog2hw[edge[0]] = best_hw_qubit
                    available_hw_qubits.remove(best_hw_qubit)
                else:
                    best_hw_qubit = self._select_best_remaining_qubit(edge[1],available_hw_qubits,prog2hw)
                    if best_hw_qubit is None:
                        raise TranspilerError(
                            "CNOT({}, {}) could not be placed in selected device. "
                            "No qubit near qr[{}] available".format(edge[0], edge[1], edge[1])
                        )
                    prog2hw[edge[1]] = best_hw_qubit
                    available_hw_qubits.remove(best_hw_qubit)

            for qid in self.qarg_to_id.values():
                if qid not in prog2hw:
                    prog2hw[qid] = available_hw_qubits[0]
                    available_hw_qubits.remove(prog2hw[qid])

            score = self._score_mapping(prog2hw)
            candidate_scores.append((score, prog2hw))

        #print(f"candidates:",candidate_scores);
        best_mapping = max(candidate_scores, key=lambda x: x[0])[1]

        layout = Layout()
        for q in dag1.qubits:
            pid = self._qarg_to_id(q)
            layout[q] = best_mapping[pid]
        for qreg in dag1.qregs.values():
            layout.add_register(qreg)
        self.property_set["layout"] = layout

        return layout, dag1, dag2



    def visualize_initial_mapping(self, circuit,layout, fpath="./output/visualize/InitialMapping/", fname="initial_mapping.png"):
        initial_layout = layout
        os.makedirs(fpath, exist_ok=True)

        # Prepare node colors: black for mapped, purple for unmapped
        qubit_colors = []
        phys_to_virt = initial_layout.get_physical_bits()  # physical -> Qubit object
        for node in range(self.backend.configuration().n_qubits):
            if node in phys_to_virt:
                qubit_colors.append('black')  # mapped
            else:
                qubit_colors.append('purple')  # unmapped

        # Plot gate map
        fig_gate = plot_gate_map(self.backend, label_qubits=True, qubit_color=qubit_colors)
        bit_locations = {
            bit: {"register": register, "index": index}
            for register in initial_layout.get_registers()
            for index, bit in enumerate(register)
        }

        # Convert layout dict to string for display
        layout_str = "Physical -> Virtual:\n"
        for phys, virt in phys_to_virt.items():
            bit_register = bit_locations[virt]["register"]
            if bit_register is None or bit_register.name != "ancilla":
                layout_str += f"{phys} -> {str(bit_locations[virt]["register"].name)+"_"+str(bit_locations[virt]["index"])}\n"
        # Add the layout text next to the figure
        fig_gate.text(1.05, 0.5, layout_str, rotation=0, fontsize=12, va='center', ha='left')
        fig_gate.suptitle(circuit.name, fontsize=14)
        # Save figure
        save_path = os.path.join(fpath, fname)
        fig_gate.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close(fig_gate)
        print(f"Saved combined figure to {save_path}")
