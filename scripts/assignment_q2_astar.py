"""Q2: A*, uniform-cost and greedy best-first on the robot graph. Prints the traces."""

import heapq

G = {
    "S0": {"S1": 3, "S2": 2},
    "S1": {"S0": 3, "S3": 3},
    "S2": {"S0": 2, "S3": 4, "S4": 2},
    "S3": {"S1": 3, "S2": 4, "S4": 6, "S5": 3},
    "S4": {"S2": 2, "S3": 6},
    "S5": {"S3": 3},
}
H = {"S0": 5, "S1": 4, "S2": 3, "S3": 2, "S4": 1, "S5": 0}


def search(kind: str):
    w_g = 0 if kind == "greedy" else 1
    w_h = 0 if kind == "ucs" else 1
    g = {"S0": 0}
    parent = {"S0": None}
    frontier = [(w_g * 0 + w_h * H["S0"], 0, "S0")]
    closed: list[str] = []
    print(f"\n=== {kind.upper()} ===")
    step = 0
    while frontier:
        f, gc, n = heapq.heappop(frontier)
        if n in closed:
            continue
        closed.append(n)
        step += 1
        print(
            f"step {step}: expand {n}  g={gc}  h={H[n]}  f={f}   frontier after pop: {sorted((round(x[0], 1), x[2]) for x in frontier if x[2] not in closed)}"
        )
        if n == "S5":
            path = []
            while n:
                path.append(n)
                n = parent[n]
            path.reverse()
            cost = sum(G[a][b] for a, b in zip(path, path[1:], strict=False))
            print(f"GOAL. path {' -> '.join(path)}  cost {cost}  nodes expanded {len(closed)}")
            return path, cost, len(closed)
        for m, c in G[n].items():
            ng = gc + c
            if kind == "greedy":
                if m not in closed and m not in parent:
                    parent[m] = n
                    heapq.heappush(frontier, (H[m], ng, m))
            elif m not in g or ng < g[m]:
                g[m] = ng
                parent[m] = n
                heapq.heappush(frontier, (w_g * ng + w_h * H[m], ng, m))
                print(f"   push {m}  g={ng}  h={H[m]}  f={w_g * ng + w_h * H[m]}  (via {n})")


# admissibility / consistency check
def true_cost(src):
    dist = {src: 0}
    pq = [(0, src)]
    while pq:
        d, u = heapq.heappop(pq)
        for v, c in G[u].items():
            if d + c < dist.get(v, 1e9):
                dist[v] = d + c
                heapq.heappush(pq, (d + c, v))
    return dist["S5"]


print("admissibility: h(n) <= h*(n)?")
for n in G:
    print(f"  {n}: h={H[n]}  h*={true_cost(n)}  {'ok' if H[n] <= true_cost(n) else 'VIOLATED'}")
print("consistency: h(n) <= c(n,m) + h(m) for every edge?")
bad = [(n, m) for n in G for m in G[n] if H[n] > G[n][m] + H[m]]
print("  violations:", bad or "none")

for k in ("astar", "ucs", "greedy"):
    search(k)
