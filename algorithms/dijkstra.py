import heapq
import math


def dijkstra(graph, source, capture_steps=False):
    if source not in graph.adj:
        raise ValueError(f"Unknown source node: {source}")
    dist = {node: math.inf for node in graph.nodes()}
    prev = {node: None for node in graph.nodes()}
    dist[source] = 0.0
    pq = [(0.0, source)]
    visited = set()
    steps = []

    while pq:
        current_dist, u = heapq.heappop(pq)
        if u in visited:
            continue
        visited.add(u)
        if capture_steps:
            steps.append(f"Select {u} with tentative distance {current_dist:.2f} min")
        for v, w in graph.neighbors(u):
            nd = current_dist + w
            if nd < dist[v]:
                old = dist[v]
                dist[v] = nd
                prev[v] = u
                heapq.heappush(pq, (nd, v))
                if capture_steps:
                    old_text = "∞" if math.isinf(old) else f"{old:.2f}"
                    steps.append(f"Update {v}: {old_text} → {nd:.2f} min via {u}")
    return dist, prev, steps


def reconstruct_path(prev, source, destination):
    if source == destination:
        return [source]
    path = []
    cur = destination
    while cur is not None:
        path.append(cur)
        if cur == source:
            break
        cur = prev.get(cur)
    if not path or path[-1] != source:
        return []
    return list(reversed(path))


def shortest_path(graph, source, destination):
    dist, prev, steps = dijkstra(graph, source, capture_steps=True)
    return dist.get(destination, math.inf), reconstruct_path(prev, source, destination), steps
