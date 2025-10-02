from __future__ import annotations
from typing import Tuple

Grid = Tuple[Tuple[int,...], ...]

class HCeilHalf:
    """Heuristic: ceil(H/2) với H = số ô sai vị trí (không tính ô trống)."""
    def __init__(self, goal: Grid):
        self.goal = goal
        self.pos = {}
        for r in range(3):
            for c in range(3):
                self.pos[goal[r][c]] = (r,c)

    def h(self, state: Grid) -> float:
        H = 0
        for r in range(3):
            for c in range(3):
                v = state[r][c]
                if v == 0:
                    continue
                if self.pos[v] != (r,c):
                    H += 1
        return (H + 1) // 2  # ceil(H/2)

class HPDBStub:
    """PDB stub: nhóm sẽ thay bằng PDB thật (additive)."""
    def h(self, state: Grid) -> float:
        return 0.0
