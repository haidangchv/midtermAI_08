# ===============================================================
#  Heuristics for A* 8-Puzzle (4 goal states + special move rules)
# ===============================================================

from __future__ import annotations
from typing import Tuple, List, Dict, Iterable, Set
from collections import deque

# -----------------------------
# I. Kiểu dữ liệu và cấu trúc
# -----------------------------
GridMatrix = Tuple[Tuple[int, ...], ...]  # 3x3 ma trận (0 = blank)
GridFlat   = Tuple[int, ...]              # dạng phẳng 9 phần tử

# -----------------------------
# II. Heuristic 1: ceil(H/2)
# -----------------------------
class HCeilHalf:
    """
    H1 = ceil(H/2)
    với H = số ô sai vị trí (không tính ô trống),
    min qua 4 goal.
    """
    def __init__(self, goals: List[GridMatrix]):
        self.pos_list: List[Dict[int, Tuple[int,int]]] = []
        for goal in goals:
            pos = {}
            for r in range(3):
                for c in range(3):
                    pos[goal[r][c]] = (r, c)
            self.pos_list.append(pos)

    def h(self, state: GridMatrix) -> float:
        best = 10**9
        for pos in self.pos_list:
            H = 0
            for r in range(3):
                for c in range(3):
                    v = state[r][c]
                    if v != 0 and pos[v] != (r, c):
                        H += 1
            best = min(best, (H + 1)//2)  # ceil(H/2)
        return float(best)

# -----------------------------
# III. Công cụ cho Pattern DB
# -----------------------------
ADJ = {
    0:(1,3), 1:(0,2,4), 2:(1,5),
    3:(0,4,6), 4:(1,3,5,7), 5:(2,4,8),
    6:(3,7), 7:(4,6,8), 8:(5,7)
}
DIAG_PAIRS = [(0,8),(2,6)]  # cặp góc chéo
SUM9 = {(1,8),(2,7),(3,6),(4,5)}  # các cặp A+B=9

def _swap(s: GridFlat, i: int, j: int) -> GridFlat:
    if i == j: return s
    a = list(s)
    a[i], a[j] = a[j], a[i]
    return tuple(a)

def flatten(m: GridMatrix) -> GridFlat:
    return tuple(v for row in m for v in row)

def unflatten(s: GridFlat) -> GridMatrix:
    return (tuple(s[0:3]), tuple(s[3:6]), tuple(s[6:9]))

# -----------------------------
# IV. Sinh hàng xóm (3 luật)
# -----------------------------
def neighbors_flat(s: GridFlat) -> Iterable[GridFlat]:
    """Sinh hàng xóm theo 3 luật: slide blank, swap (A+B=9), swap góc chéo."""
    # 1) slide blank
    z = s.index(0)
    for j in ADJ[z]:
        yield _swap(s, z, j)
    # 2) swap A+B=9 (kề nhau, không dính blank)
    for i in range(9):
        vi = s[i]
        if vi == 0: continue
        for j in ADJ[i]:
            vj = s[j]
            if vj != 0 and vi + vj == 9:
                yield _swap(s, i, j)
    # 3) swap góc chéo
    for i,j in DIAG_PAIRS:
        if s[i] != 0 and s[j] != 0:
            yield _swap(s, i, j)

# -----------------------------
# V. Pattern Key và tiện ích PDB
# -----------------------------
def pattern_key(state_flat: GridFlat, pattern: Tuple[int, ...]) -> Tuple[int, ...]:
    pos = [-1] * 9
    for idx, v in enumerate(state_flat):
        pos[v] = idx
    return tuple(pos[t] for t in pattern)

def grids_to_flat(goals: List[GridMatrix]) -> List[GridFlat]:
    return [flatten(g) for g in goals]

# -----------------------------
# VI. Partial Pattern Database
# -----------------------------
class PartialPDB:
    """
    Reverse-BFS từ tập goal.
    Lưu projection theo 'pattern' (chỉ các tile quan tâm).
    """
    def __init__(self, pattern: Tuple[int, ...], goals: List[GridMatrix], max_states: int = 200_000):
        self.pattern = pattern
        self.table: Dict[Tuple[int, ...], int] = {}
        self._build(grids_to_flat(goals), max_states)

    def _build(self, goals_flat: List[GridFlat], max_states: int):
        q = deque()
        seen: Set[GridFlat] = set()

        # Seed từ nhiều goal
        for g in goals_flat:
            key = pattern_key(g, self.pattern)
            self.table[key] = 0
            q.append(g)
            seen.add(g)

        # Reverse BFS
        while q and len(seen) < max_states:
            s = q.popleft()
            d = self.table.get(pattern_key(s, self.pattern), 0)
            for t in neighbors_flat(s):
                if t in seen: continue
                seen.add(t)
                q.append(t)
                k = pattern_key(t, self.pattern)
                if k not in self.table:
                    self.table[k] = d + 1

    def h_flat(self, s: GridFlat) -> int:
        return self.table.get(pattern_key(s, self.pattern), 0)

# -----------------------------
# VII. Heuristic 2: Additive PDB
# -----------------------------
class HPDBAdditive:
    """
    H2 = tổng hai PDB rời nhau (1,2,3,4) & (5,6,7,8)
    Admissible: vì tổng hai cận dưới độc lập.
    """
    def __init__(self, goals: List[GridMatrix],
                 pat1: Tuple[int, ...]=(1,2,3,4),
                 pat2: Tuple[int, ...]=(5,6,7,8),
                 max_states: int = 200_000):
        self.p1 = PartialPDB(pat1, goals, max_states=max_states)
        self.p2 = PartialPDB(pat2, goals, max_states=max_states)

    def h(self, state: GridMatrix) -> float:
        s = flatten(state)
        return float(self.p1.h_flat(s) + self.p2.h_flat(s))

# -----------------------------
# VIII. Heuristic kết hợp
# -----------------------------
class HMax:
    """Kết hợp cận dưới mạnh hơn: max(h1, h2)."""
    def __init__(self, h1, h2):
        self.h1, self.h2 = h1, h2
    def h(self, s: GridMatrix) -> float:
        return max(self.h1.h(s), self.h2.h(s))
