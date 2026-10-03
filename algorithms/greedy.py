from .dijkstra import dijkstra


def greedy_station_placement(graph, station_count, target_time):
    nodes = graph.nodes()
    if not nodes:
        return [], [], {}, {"dijkstra_runs": 0, "candidate_evaluations": 0}
    station_count = min(max(1, int(station_count)), len(nodes))
    target_time = float(target_time)

    coverage_cache = {}
    dijkstra_runs = 0
    for node in nodes:
        dist, _, _ = dijkstra(graph, node)
        dijkstra_runs += 1
        coverage_cache[node] = {n for n, d in dist.items() if d <= target_time}

    selected = []
    covered = set()
    decision_log = []
    candidate_evaluations = 0

    for step in range(1, station_count + 1):
        rows = []
        best = None
        best_new = set()
        for candidate in nodes:
            if candidate in selected:
                continue
            new_nodes = coverage_cache[candidate] - covered
            candidate_evaluations += 1
            rows.append({
                "step": step,
                "candidate": candidate,
                "new_coverage": len(new_nodes),
                "total_coverage_if_selected": len(covered | coverage_cache[candidate]),
            })
            if best is None or len(new_nodes) > len(best_new) or (len(new_nodes) == len(best_new) and candidate < best):
                best = candidate
                best_new = new_nodes
        if best is None:
            break
        selected.append(best)
        covered |= coverage_cache[best]
        decision_log.append({
            "step": step,
            "selected": best,
            "new_coverage": len(best_new),
            "covered_after": len(covered),
            "candidates": sorted(rows, key=lambda x: (-x["new_coverage"], x["candidate"])),
        })

    stats = {"dijkstra_runs": dijkstra_runs, "candidate_evaluations": candidate_evaluations}
    return selected, decision_log, coverage_cache, stats
