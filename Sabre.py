from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
#from qiskit_ibm_catalog import QiskitServerless, QiskitFunction
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import EstimatorOptions
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout, SabreSwap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import matplotlib.pyplot as plt
import numpy as np
import time
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2, FakeWashingtonV2

# set seed for reproducibility
seed = 42
num_qubits = 10

# Create GHZ circuit
qc = QuantumCircuit(num_qubits)
qc.h(0)
for i in range(1, num_qubits):
    qc.cx(0, i)

qc.measure_all()


# ZZII...II, ZIZI...II, ... , ZIII...IZ
operator_strings = [
    "Z" + "I" * i + "Z" + "I" * (num_qubits - 2 - i)
    for i in range(num_qubits - 1)
]
print(operator_strings)
print(len(operator_strings))

operators = [SparsePauliOp(operator) for operator in operator_strings]



backend = FakeGuadalupeV2()

# Get the coupling map from the backend
cmap = backend.coupling_map

# Create the SabreLayout passes for the custom configurations
sl_2 = SabreLayout(
    coupling_map=cmap,
    seed=seed,
    max_iterations=4,
    layout_trials=200,
    swap_trials=200,
)
sl_3 = SabreLayout(
    coupling_map=cmap,
    seed=seed,
    max_iterations=8,
    layout_trials=200,
    swap_trials=200,
)

# Create the pass managers, need to first create then configure the SabreLayout passes
pm_1 = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=seed
)
pm_2 = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=seed
)
pm_3 = generate_preset_pass_manager(
    optimization_level=3, backend=backend, seed_transpiler=seed
)

pm_2.layout.replace(index=2, passes=sl_2)
pm_3.layout.replace(index=2, passes=sl_3)


# Transpile the circuit with each pass manager and measure the time
t0 = time.time()
tqc_1 = pm_1.run(qc)
t1 = time.time() - t0
t0 = time.time()
tqc_2 = pm_2.run(qc)
t2 = time.time() - t0
t0 = time.time()
tqc_3 = pm_3.run(qc)
t3 = time.time() - t0

# Obtain the depths and the total number of gates (circuit size)
depth_1 = tqc_1.depth(lambda x: x.operation.num_qubits == 2)
depth_2 = tqc_2.depth(lambda x: x.operation.num_qubits == 2)
depth_3 = tqc_3.depth(lambda x: x.operation.num_qubits == 2)
size_1 = tqc_1.size()
size_2 = tqc_2.size()
size_3 = tqc_3.size()

# Transform the observables to match the backend's ISA
operators_list_1 = [op.apply_layout(tqc_1.layout) for op in operators]
operators_list_2 = [op.apply_layout(tqc_2.layout) for op in operators]
operators_list_3 = [op.apply_layout(tqc_3.layout) for op in operators]

# Compute improvements compared to pass manager 1 (default)
depth_improvement_2 = ((depth_1 - depth_2) / depth_1) * 100
depth_improvement_3 = ((depth_1 - depth_3) / depth_1) * 100
size_improvement_2 = ((size_1 - size_2) / size_1) * 100
size_improvement_3 = ((size_1 - size_3) / size_1) * 100
time_increase_2 = ((t2 - t1) / t1) * 100
time_increase_3 = ((t3 - t1) / t1) * 100

print(
    f"Pass manager 1 (4,20,20)  : Depth {depth_1}, Size {size_1}, Time {t1:.4f} s"
)
print(
    f"Pass manager 2 (4,200,200): Depth {depth_2}, Size {size_2}, Time {t2:.4f} s"
)
print(f"  - Depth improvement: {depth_improvement_2:.2f}%")
print(f"  - Size improvement: {size_improvement_2:.2f}%")
print(f"  - Time increase: {time_increase_2:.2f}%")
print(
    f"Pass manager 3 (8,200,200): Depth {depth_3}, Size {size_3}, Time {t3:.4f} s"
)
print(f"  - Depth improvement: {depth_improvement_3:.2f}%")
print(f"  - Size improvement: {size_improvement_3:.2f}%")
print(f"  - Time increase: {time_increase_3:.2f}%")


options = EstimatorOptions()
options.resilience_level = 1
options.dynamical_decoupling.enable = True
options.dynamical_decoupling.sequence_type = "XY4"

# Create an Estimator object
estimator = Estimator(backend, options=options)


# Submit the circuit to Estimator
job_1 = estimator.run([(tqc_1, operators_list_1)])
job_1_id = job_1.job_id()
print(job_1_id)

job_2 = estimator.run([(tqc_2, operators_list_2)])
job_2_id = job_2.job_id()
print(job_2_id)

job_3 = estimator.run([(tqc_3, operators_list_3)])
job_3_id = job_3.job_id()
print(job_3_id)


# Run the jobs
result_1 = job_1.result()[0]
print("Job 1 done")
result_2 = job_2.result()[0]
print("Job 2 done")
result_3 = job_3.result()[0]
print("Job 3 done")


data = list(range(1, len(operators) + 1))  # Distance between the Z operators

# Normalize and process expectation values for each result
values_1 = [v / result_1.data.evs[0] for v in result_1.data.evs]
values_2 = [v / result_2.data.evs[0] for v in result_2.data.evs]
values_3 = [v / result_3.data.evs[0] for v in result_3.data.evs]

plt.plot(
    data,
    values_1,
    marker="o",
    label="pm_1 (iters=4, swap_trials=20, layout_trials=20)",
)
plt.plot(
    data,
    values_2,
    marker="s",
    label="pm_2 (iters=4, swap_trials=200, layout_trials=200)",
)
plt.plot(
    data,
    values_3,
    marker="^",
    label="pm_3 (iters=8, swap_trials=200, layout_trials=200)",
)
plt.xlabel("Distance between qubits $i$")
plt.ylabel(r"$\langle Z_i Z_0 \rangle / \langle Z_1 Z_0 \rangle $")
plt.legend()
plt.show()
