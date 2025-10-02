from __future__ import annotations
from typing import Tuple, List
from collections import deque

Pos = Tuple[int,int]
Grid = List[str]

def bfs_dist(grid: Grid, start: Pos, goal: Pos) -> int:
    R, C = len(grid), len(grid[0])
    q = deque([(start,0)]); seen = {start}
    while q:
        (r,c), d = q.popleft()
        if (r,c) == goal:
            return d
        for dr,dc in [(1,0),(-1,0),(0,1),(0,-1)]:
            nr, nc = r+dr, c+dc
            if 0 <= nr < R and 0 <= nc < C and grid[nr][nc] != '%' and (nr,nc) not in seen:
                seen.add((nr,nc)); q.append(((nr,nc), d+1))
    return 10**9

def mst_lower_bound(grid: Grid, points: List[Pos]) -> int:
    if not points: return 0
    n = len(points)
    in_mst = [False]*n
    dist = [10**9]*n
    dist[0] = 0
    total = 0
    for _ in range(n):
        u = min((i for i in range(n) if not in_mst[i]), key=lambda i: dist[i])
        in_mst[u] = True
        total += dist[u]
        for v in range(n):
            if not in_mst[v]:
                w = bfs_dist(grid, points[u], points[v])
                if w < dist[v]:
                    dist[v] = w
    return total

class HeuristicPacmanMST:
    def __init__(self, static_grid: Grid, exit_pos: Pos):
        self.grid = static_grid
        self.exit = exit_pos

    def h(self, state) -> float:
        pts = [state.pacman] + list(state.foods) + [self.exit]
        return float(mst_lower_bound(self.grid, pts))
