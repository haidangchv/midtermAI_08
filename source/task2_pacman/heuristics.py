# source/task2_pacman/heuristics.py

from functools import lru_cache
from collections import deque

def _neighbors(g, r, c):
    R,C = len(g), len(g[0])
    for dr,dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < R and 0 <= nc < C and g[nr][nc] != '%':
            yield nr, nc

def _bfs_dist(g, src, dst):
    if src == dst: return 0
    q = deque([src])
    seen = {src:0}
    while q:
        r,c = q.popleft()
        for nr,nc in _neighbors(g,r,c):
            if (nr,nc) in seen: continue
            seen[(nr,nc)] = seen[(r,c)] + 1
            if (nr,nc) == dst:
                return seen[(nr,nc)]
            q.append((nr,nc))
    return float("inf")

class HeuristicMazeMST:
    """
    h(s) = min_teleportaware(Pac→nearest food) + MST(foods∪{Exit}) theo maze-dist.
    Nếu không còn food: h(s) = min_teleportaware(Pac→Exit).
    Teleport-aware: dist_T(p,q) = min( dist_maze(p,q), 1 + min_a dist_maze(p,a) + dist_maze(a,q) )
    với a là một trong 4 'neo teleport' của lưới hiện tại.
    -> Vẫn admissible vì luôn là cận dưới chi phí thật (teleport có cost 1).
    """
    def __init__(self, problem):
        self.problem = problem

    @lru_cache(maxsize=200_000)
    def _dist(self, rot_idx, a, b):
        g = self.problem._current_grid(rot_idx)
        return _bfs_dist(g, a, b)

    def _teleport_aware(self, rot_idx, p, q):
        # cơ bản: đi thường
        best = self._dist(rot_idx, p, q)
        # xét qua 4 neo hiện tại
        anchors = self.problem._corner_anchor_positions(rot_idx).values()
        via = min(
            self._dist(rot_idx, p, a) + 1 + self._dist(rot_idx, a, q)
            for a in anchors
        )
        return min(best, via)

    def _mst_len(self, rot_idx, points):
        # Prim đơn giản, dùng maze-dist thường (không cần teleport để giữ admissible).
        pts = list(points)
        if len(pts) <= 1: return 0
        used = {pts[0]}
        total = 0
        while len(used) < len(pts):
            best = float("inf"); addp = None
            for u in used:
                for v in pts:
                    if v in used: continue
                    d = self._dist(rot_idx, u, v)
                    if d < best:
                        best, addp = d, v
            total += best
            used.add(addp)
        return total

    def h(self, s):
        rot = s.rot_idx
        ex  = self.problem._exit_at(rot)
        pac = s.pacman
        foods = tuple(s.foods)

        if not foods:
            return self._teleport_aware(rot, pac, ex)

        # Pac → food gần nhất (teleport-aware)
        dmin = min(self._teleport_aware(rot, pac, f) for f in foods)
        # MST trên foods ∪ {Exit} (maze-dist thường, vẫn admissible)
        mst  = self._mst_len(rot, set(foods) | {ex})
        return dmin + mst


class HeuristicZero:
    def h(self, s): return 0
