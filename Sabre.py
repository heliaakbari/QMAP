from qiskit import QuantumCircuit
from qiskit.quantum_info import SparsePauliOp
from test.benchmarks.qft import build_model_circuit
from test.benchmarks.ripple_adder import build_ripple_adder_circuit
#from qiskit_ibm_catalog import QiskitServerless, QiskitFunction
from qiskit_ibm_runtime import QiskitRuntimeService
from qiskit_ibm_runtime import EstimatorOptions
from qiskit_ibm_runtime import EstimatorV2 as Estimator
from qiskit.transpiler import CouplingMap
from qiskit.transpiler.passes import SabreLayout, HASwap, SabreSwap
from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
import matplotlib.pyplot as plt
import numpy as np
import time
from qiskit_ibm_runtime.fake_provider import FakeGuadalupeV2, FakeWashingtonV2

# set seed for reproducibility
seed = 42
digits = 6
optimization_level = 1
# Create GHZ circuit
qc = build_ripple_adder_circuit(digits)
num_qubits = qc.num_qubits

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

# Create the SabreLayout passes for the custom configurations
# sl_1 = SabreLayout(
#     coupling_map=backend.target,
#     seed=seed,
#     max_iterations=4,
#     layout_trials=200,
#     swap_trials=200,
# )

ss_1 = SabreSwap(coupling_map=backend.target,seed=seed,heuristic="basic",trials=1)
ss_2 = SabreSwap(coupling_map=backend.target,seed=seed,heuristic="lookahead",trials=2)
ss_3 = SabreSwap(coupling_map=backend.target,seed=seed,heuristic="decay",trials=5)

has_1 = HASwap(coupling_map=backend.target,seed=seed,heuristic="basic",trials=1)
has_2 = HASwap(coupling_map=backend.target,seed=seed,heuristic="lookahead",trials=2)
has_3 = HASwap(coupling_map=backend.target,seed=seed,heuristic="decay",trials=5)

# Create the pass managers, need to first create then configure the SabreLayout passes
pm_1 = generate_preset_pass_manager(
    optimization_level=optimization_level, backend=backend, seed_transpiler=seed
)

pm_2 = generate_preset_pass_manager(
    optimization_level=optimization_level, backend=backend, seed_transpiler=seed
)

pm_3 = generate_preset_pass_manager(
    optimization_level=optimization_level, backend=backend, seed_transpiler=seed
)

pmha_1 = generate_preset_pass_manager(
    optimization_level=optimization_level, backend=backend, seed_transpiler=seed
)

pmha_2 = generate_preset_pass_manager(
    optimization_level=optimization_level, backend=backend, seed_transpiler=seed
)

pmha_3 = generate_preset_pass_manager(
    optimization_level=optimization_level, backend=backend, seed_transpiler=seed
)

print(pm_1.routing)
#pm_1.layout.replace(index=1, passes=sl_1)

pm_1.routing.replace(index=3, passes=ss_1)
pmha_1.routing.replace(index=3, passes=has_1)
pm_2.routing.replace(index=3, passes=ss_2)
pmha_2.routing.replace(index=3, passes=has_2)
pm_3.routing.replace(index=3, passes=ss_3)
pmha_3.routing.replace(index=3, passes=has_3)

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

# --- Run pmha_1 through pmha_3 ---
t0 = time.time()
tqc_ha_1 = pmha_1.run(qc)
tha_1 = time.time() - t0

t0 = time.time()
tqc_ha_2 = pmha_2.run(qc)
tha_2 = time.time() - t0

t0 = time.time()
tqc_ha_3 = pmha_3.run(qc)
tha_3 = time.time() - t0

# Obtain the depths and the total number of gates (circuit size)
depth_1 = tqc_1.depth(lambda x: x.operation.num_qubits == 2)
depth_2 = tqc_2.depth(lambda x: x.operation.num_qubits == 2)
depth_3 = tqc_3.depth(lambda x: x.operation.num_qubits == 2)

depth_ha_1 = tqc_ha_1.depth(lambda x: x.operation.num_qubits == 2)
depth_ha_2 = tqc_ha_2.depth(lambda x: x.operation.num_qubits == 2)
depth_ha_3 = tqc_ha_3.depth(lambda x: x.operation.num_qubits == 2)

size_1 = tqc_1.size()
size_2 = tqc_2.size()
size_3 = tqc_3.size()

size_ha_1 = tqc_ha_1.size()
size_ha_2 = tqc_ha_2.size()
size_ha_3 = tqc_ha_3.size()

operators_list_1 = [op.apply_layout(tqc_1.layout) for op in operators]
operators_list_2 = [op.apply_layout(tqc_2.layout) for op in operators]
operators_list_3 = [op.apply_layout(tqc_3.layout) for op in operators]
operators_list_ha_1 = [op.apply_layout(tqc_ha_1.layout) for op in operators]
operators_list_ha_2 = [op.apply_layout(tqc_ha_2.layout) for op in operators]
operators_list_ha_3 = [op.apply_layout(tqc_ha_3.layout) for op in operators]

# Compute improvements compared to pass manager 1 (default)
depth_improvement_2 = ((depth_1 - depth_2) / depth_1) * 100
depth_improvement_3 = ((depth_1 - depth_3) / depth_1) * 100
depth_improvement_ha_1 = ((depth_1 - depth_ha_1) / depth_1) * 100
depth_improvement_ha_2 = ((depth_1 - depth_ha_2) / depth_1) * 100
depth_improvement_ha_3 = ((depth_1 - depth_ha_3) / depth_1) * 100

size_improvement_2 = ((size_1 - size_2) / size_1) * 100
size_improvement_3 = ((size_1 - size_3) / size_1) * 100
size_improvement_ha_1 = ((size_1 - size_ha_1) / size_1) * 100
size_improvement_ha_2 = ((size_1 - size_ha_2) / size_1) * 100
size_improvement_ha_3 = ((size_1 - size_ha_3) / size_1) * 100

time_increase_2 = ((t2 - t1) / t1) * 100
time_increase_3 = ((t3 - t1) / t1) * 100
time_increase_ha_1 = ((tha_1 - t1) / t1) * 100
time_increase_ha_2 = ((tha_2 - t1) / t1) * 100
time_increase_ha_3 = ((tha_3 - t1) / t1) * 100

# Print results
print(f"Pass manager 1 (4,20,20)    : Depth {depth_1}, Size {size_1}, Time {t1:.4f} s")
print(f"Pass manager 2 (4,200,200)  : Depth {depth_2}, Size {size_2}, Time {t2:.4f} s")
print(f"  - Depth improvement: {depth_improvement_2:.2f}%")
print(f"  - Size improvement: {size_improvement_2:.2f}%")
print(f"  - Time increase: {time_increase_2:.2f}%")
print(f"Pass manager 3 (8,200,200)  : Depth {depth_3}, Size {size_3}, Time {t3:.4f} s")
print(f"  - Depth improvement: {depth_improvement_3:.2f}%")
print(f"  - Size improvement: {size_improvement_3:.2f}%")
print(f"  - Time increase: {time_increase_3:.2f}%")

print(f"pmha_1 (4,20,20)            : Depth {depth_ha_1}, Size {size_ha_1}, Time {tha_1:.4f} s")
print(f"  - Depth improvement: {depth_improvement_ha_1:.2f}%")
print(f"  - Size improvement: {size_improvement_ha_1:.2f}%")
print(f"  - Time increase: {time_increase_ha_1:.2f}%")
print(f"pmha_2 (4,200,200)          : Depth {depth_ha_2}, Size {size_ha_2}, Time {tha_2:.4f} s")
print(f"  - Depth improvement: {depth_improvement_ha_2:.2f}%")
print(f"  - Size improvement: {size_improvement_ha_2:.2f}%")
print(f"  - Time increase: {time_increase_ha_2:.2f}%")
print(f"pmha_3 (8,200,200)          : Depth {depth_ha_3}, Size {size_ha_3}, Time {tha_3:.4f} s")
print(f"  - Depth improvement: {depth_improvement_ha_3:.2f}%")
print(f"  - Size improvement: {size_improvement_ha_3:.2f}%")
print(f"  - Time increase: {time_increase_ha_3:.2f}%")


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

job_ha_1 = estimator.run([(tqc_ha_1, operators_list_ha_1)])
job_ha_1_id = job_ha_1.job_id()
print(job_ha_1_id)

job_ha_2 = estimator.run([(tqc_ha_2, operators_list_ha_2)])
job_ha_2_id = job_ha_2.job_id()
print(job_ha_2_id)

job_ha_3 = estimator.run([(tqc_ha_3, operators_list_ha_3)])
job_ha_3_id = job_ha_3.job_id()
print(job_ha_3_id)


# Run the jobs
result_1 = job_1.result()[0]
print("Job 1 done")
result_2 = job_2.result()[0]
print("Job 2 done")
result_3 = job_3.result()[0]
print("Job 3 done")

result_ha_1 = job_ha_1.result()[0]
print("Job ha_1 done")
result_ha_2 = job_ha_2.result()[0]
print("Job ha_2 done")
result_ha_3 = job_ha_3.result()[0]
print("Job ha_3 done")



data = list(range(1, len(operators) + 1))  # Distance between the Z operators

# Normalize and process expectation values for each result
values_1 = [v / result_1.data.evs[0] for v in result_1.data.evs]
values_2 = [v / result_2.data.evs[0] for v in result_2.data.evs]
values_3 = [v / result_3.data.evs[0] for v in result_3.data.evs]
values_ha_1 = [v / result_ha_1.data.evs[0] for v in result_ha_1.data.evs]
values_ha_2 = [v / result_ha_2.data.evs[0] for v in result_ha_2.data.evs]
values_ha_3 = [v / result_ha_3.data.evs[0] for v in result_ha_3.data.evs]


plt.plot(data, values_1, marker="o", label="pm_1 (4,20,20)")
plt.plot(data, values_2, marker="s", label="pm_2 (4,200,200)")
plt.plot(data, values_3, marker="^", label="pm_3 (8,200,200)")

plt.plot(data, values_ha_1, marker="o", linestyle="--", label="pmha_1 (4,20,20)")
plt.plot(data, values_ha_2, marker="s", linestyle="--", label="pmha_2 (4,200,200)")
plt.plot(data, values_ha_3, marker="^", linestyle="--", label="pmha_3 (8,200,200)")

plt.xlabel("Distance between qubits $i$")
plt.ylabel(r"$\langle Z_i Z_0 \rangle / \langle Z_1 Z_0 \rangle $")
plt.legend()
plt.show()
