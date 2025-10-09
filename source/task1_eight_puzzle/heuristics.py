# source/task1_eight_puzzle/heuristics.py
from __future__ import annotations
from typing import Tuple, List, Dict, Iterable, Set
from collections import deque

# ===== Kiểu dữ liệu =====
# Ma trận 3x3 (0 = ô trống)
GridMatrix = Tuple[Tuple[int, ...], ...]
# Dạng phẳng 9 phần tử
GridFlat = Tuple[int, ...]  # index = r*3 + c

# ===== Heuristic 1: ceil(H/2) =====
class HCeilHalf:
    """ceil(H/2) với H = số ô sai vị trí (không tính ô trống)."""
    def __init__(self, goal: GridMatrix):
        # map vị trí kỳ vọng của mỗi số theo goal
        self.pos: Dict[int, Tuple[int,int]] = {}
        for r in range(3):
            for c in range(3):
                self.pos[goal[r][c]] = (r, c)

    def h(self, state: GridMatrix) -> float:
        H = 0
        for r in range(3):
            for c in range(3):
                v = state[r][c]
                if v != 0 and self.pos[v] != (r, c):
                    H += 1
        return float((H + 1) // 2)  # ceil(H/2)

# ===== Công cụ dựng PDB (gộp từ heuristics_pdb.py) =====
# Kề nhau (trên/dưới/trái/phải) trong dạng phẳng 3x3
ADJ = {
    0: (1, 3),     1: (0, 2, 4),  2: (1, 5),
    3: (0, 4, 6),  4: (1, 3, 5,7),5: (2, 4, 8),
    6: (3, 7),     7: (4, 6, 8),  8: (5, 7)
}
# Cặp góc chéo cho luật swap
DIAG_PAIRS = [(0, 8), (2, 6)]  # (0,0)<->(2,2) và (0,2)<->(2,0)

def _swap(s: GridFlat, i: int, j: int) -> GridFlat:
    if i == j: return s
    a = list(s)
    a[i], a[j] = a[j], a[i]
    return tuple(a)

def neighbors_flat(s: GridFlat) -> Iterable[GridFlat]:
    """Sinh hàng xóm theo 2 luật của đề (trên dạng phẳng)."""
    # Rule 1: hai ô kề nhau, không phải 0, có tổng = 9 -> được swap
    for i in range(9):
        vi = s[i]
        if vi == 0:  # không swap với blank
            continue
        for j in ADJ[i]:
            vj = s[j]
            if vj != 0 and vi + vj == 9:
                yield _swap(s, i, j)
    # Rule 2: swap 2 góc chéo (không dính blank)
    for i, j in DIAG_PAIRS:
        if s[i] != 0 and s[j] != 0:
            yield _swap(s, i, j)

def flatten(m: GridMatrix) -> GridFlat:
    return tuple(v for row in m for v in row)

def unflatten(s: GridFlat) -> GridMatrix:
    return (tuple(s[0:3]), tuple(s[3:6]), tuple(s[6:9]))

def pattern_key(state_flat: GridFlat, pattern: Tuple[int, ...]) -> Tuple[int, ...]:
    """Key = tuple vị trí của từng tile trong pattern (0..8)."""
    pos = [-1] * 9
    for idx, v in enumerate(state_flat):
        pos[v] = idx
    return tuple(pos[t] for t in pattern)

def grids_to_flat(goals: List[GridMatrix]) -> List[GridFlat]:
    return [flatten(g) for g in goals]

class PartialPDB:
    """
    Dựng PDB bằng reverse-BFS từ TẬP goal theo đúng 2 luật swap của đề.
    Chỉ lưu projection theo 'pattern' (các tile được quan tâm).
    Key chưa thấy trong BFS -> trả 0 (admissible, nhưng yếu).
    """
    def __init__(self, pattern: Tuple[int, ...], goals: List[GridMatrix], max_states: int = 200_000):
        self.pattern: Tuple[int, ...] = pattern
        self.table: Dict[Tuple[int, ...], int] = {}
        self._build(grids_to_flat(goals), max_states)

    def _build(self, goals_flat: List[GridFlat], max_states: int):
        q = deque()
        seen: Set[GridFlat] = set()

        # seed từ nhiều goal
        for g in goals_flat:
            key = pattern_key(g, self.pattern)
            if key not in self.table:
                self.table[key] = 0
            q.append(g)
            seen.add(g)

        while q and len(seen) < max_states:
            s = q.popleft()
            d = self._lookup_exact_flat(s)
            for t in neighbors_flat(s):
                if t in seen:
                    continue
                seen.add(t)
                q.append(t)
                key = pattern_key(t, self.pattern)
                if key not in self.table:
                    self.table[key] = d + 1

    def _lookup_exact_flat(self, s: GridFlat) -> int:
        key = pattern_key(s, self.pattern)
        return self.table.get(key, 0)

    def h_flat(self, s: GridFlat) -> int:
        return self._lookup_exact_flat(s)

class HPDBAdditive:
    """
    PDB cộng dồn 2 pattern rời (mặc định: (1,2,3,4) và (5,6,7,8)).
    Admissible: tổng hai cận dưới độc lập.
    """
    def __init__(self,
                 goals: List[GridMatrix],
                 pat1: Tuple[int, ...] = (1,2,3,4),
                 pat2: Tuple[int, ...] = (5,6,7,8),
                 max_states: int = 200_000):
        self.p1 = PartialPDB(pat1, goals, max_states=max_states)
        self.p2 = PartialPDB(pat2, goals, max_states=max_states)

    def h(self, state: GridMatrix) -> float:
        s = flatten(state)
        return float(self.p1.h_flat(s) + self.p2.h_flat(s))

# ===== Heuristic kết hợp: max(h1, h2) =====
class HMax:
    """Kết hợp cận dưới mạnh hơn: max(h1, h2)."""
    def __init__(self, h1, h2):
        self.h1, self.h2 = h1, h2
    def h(self, s: GridMatrix) -> float:
        return max(self.h1.h(s), self.h2.h(s))
