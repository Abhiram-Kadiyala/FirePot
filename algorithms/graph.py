from collections import defaultdict

class WeightedGraph:
    def __init__(self):
        self.adj = defaultdict(list)

    def add_node(self, node):
        _ = self.adj[node]

    def add_edge(self, u, v, weight):
        if weight <= 0:
            raise ValueError("Road time must be greater than 0")
        self.adj[u].append((v, float(weight)))
        self.adj[v].append((u, float(weight)))

    def nodes(self):
        return list(self.adj.keys())

    def neighbors(self, node):
        return self.adj.get(node, [])

    def edge_count(self):
        return sum(len(v) for v in self.adj.values()) // 2


def build_graph(neighborhoods_df, roads_df):
    g = WeightedGraph()
    valid_nodes = set(neighborhoods_df["id"].astype(str))
    for node in valid_nodes:
        g.add_node(node)
    seen = set()
    for _, row in roads_df.iterrows():
        u, v = str(row["from"]), str(row["to"])
        if u not in valid_nodes or v not in valid_nodes:
            raise ValueError(f"Road references unknown neighborhood: {u} - {v}")
        if u == v:
            continue
        key = tuple(sorted((u, v)))
        if key in seen:
            continue
        seen.add(key)
        g.add_edge(u, v, float(row["time"]))
    return g
