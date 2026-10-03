import math
from algorithms.dijkstra import dijkstra


def calculate_coverage(graph, stations, target_time):
    nodes = graph.nodes()
    if not nodes or not stations:
        return {
            "total": len(nodes), "covered": 0, "uncovered": len(nodes), "coverage_pct": 0.0,
            "avg_response": math.inf, "max_covered_response": math.inf, "within_5": 0,
            "within_8": 0, "within_10": 0, "details": {}, "dijkstra_runs": 0,
        }
    station_dists = {}
    runs = 0
    for s in stations:
        station_dists[s], _, _ = dijkstra(graph, s)
        runs += 1
    details = {}
    covered_times = []
    all_finite_times = []
    for n in nodes:
        choices = [(station_dists[s].get(n, math.inf), s) for s in stations]
        best_time, best_station = min(choices)
        is_covered = best_time <= target_time
        if math.isfinite(best_time):
            all_finite_times.append(best_time)
        if is_covered:
            covered_times.append(best_time)
        details[n] = {"covered": is_covered, "time": best_time, "closest_station": best_station}
    covered = len(covered_times)
    total = len(nodes)
    finite_avg = sum(all_finite_times) / len(all_finite_times) if all_finite_times else math.inf
    return {
        "total": total,
        "covered": covered,
        "uncovered": total - covered,
        "coverage_pct": covered / total * 100 if total else 0.0,
        "avg_response": finite_avg,
        "max_covered_response": max(covered_times) if covered_times else math.inf,
        "within_5": sum(1 for x in all_finite_times if x <= 5),
        "within_8": sum(1 for x in all_finite_times if x <= 8),
        "within_10": sum(1 for x in all_finite_times if x <= 10),
        "details": details,
        "dijkstra_runs": runs,
    }
