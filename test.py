ha_manager = generate_preset_pass_manager(backend=backend, optimization_level=0)
greedy_layout_routing = GreedyLayout(seed=42, coupling_map=backend, routing_pass=HASwap(seed=42, coupling_map=backend.target, fake_run=True, heuristic="decay", trials=10),max_iterations=5, k=20, skip_routing=True, numsplit=j)
ha_swap = HASwap(seed=42,coupling_map=backend.target, heuristic="decay", trials=10, fake_run=False),
ha_manager.layout = greedy_layout_routing
ha_manager.routing = ha_swap
ha_circuit = ha_manager.run(qc)
