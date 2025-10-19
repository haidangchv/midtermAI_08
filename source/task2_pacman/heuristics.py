from collections import deque

# --- Heuristic động: BFS + teleport + eat wall ---
def _neighbors_dyn_with_teleport(grid, p, anchors):
    """4-neighbors trên grid (không đi vào '%'); nếu p là anchor -> có các cạnh teleport."""
    R, C = len(grid), len(grid[0])
    r, c = p
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] != '%':
            yield (nr, nc)
    if p in anchors.values():
        for q in anchors.values():
            if q != p:
                yield q

def _bfs_dyn_with_teleport(grid, src, dst, anchors) -> int:
    if src == dst:
        return 0
    dq = deque([src])
    dist = {src: 0}
    while dq:
        u = dq.popleft()
        for v in _neighbors_dyn_with_teleport(grid, u, anchors):
            if v not in dist:
                dist[v] = dist[u] + 1
                if v == dst:
                    return dist[v]
                dq.append(v)
    return 10**9  # unreachable

def _prim_mst_cost(nodes, dfunc) -> int:
    n = len(nodes)
    if n <= 1:
        return 0
    used = [False]*n
    best = [10**9]*n
    best[0] = 0
    total = 0
    for _ in range(n):
        u = -1; bu = 10**9
        for i in range(n):
            if not used[i] and best[i] < bu:
                bu = best[i]; u = i
        used[u] = True
        total += best[u]
        for v in range(n):
            if not used[v]:
                w = dfunc(nodes[u], nodes[v])
                if w < best[v]:
                    best[v] = w
    return total

class HeuristicPacmanMST:

    def __init__(self, problem=None, **kwargs):
        self.problem = problem

    def _d(self, grid, anchors, u, v) -> int:
        return _bfs_dyn_with_teleport(grid, u, v, anchors)

    def h(self, s) -> int:
        if self.problem is None:
            return 0 

        pac = s.pacman
        foods = list(s.foods)
        exit_pos = self.problem._exit_at(s.rot_idx)

        # Lưới động
        g = self.problem._grid_with_destruction(s)
        anchors = self.problem._corner_anchor_positions(s)

        # Nếu không còn food: chỉ còn đường tới exit
        if not foods:
            d_exit = self._d(g, anchors, pac, exit_pos)
            return 0 if d_exit >= 10**8 else d_exit

        # S = foods ∪ {exit}
        nodes = foods + [exit_pos]

        # min distance từ pac tới S (teleport-aware)
        mind = min(self._d(g, anchors, pac, x) for x in nodes)

        # MST
        def dfunc(a, b): return self._d(g, anchors, a, b)
        mst_cost = _prim_mst_cost(nodes, dfunc)

        ans = mind + mst_cost
        return 0 if ans >= 10**8 else ans

