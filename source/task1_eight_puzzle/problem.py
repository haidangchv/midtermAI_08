from __future__ import annotations
from typing import List, Tuple, Iterable

Grid = Tuple[Tuple[int,...], ...]  # 3x3, 0 = blank

class EightPuzzleProblem:
    def __init__(self, initial: Grid, goals: List[Grid]):
        self._initial = initial
        self._goals = set(goals)

    def initial_state(self) -> Grid: return self._initial
    def is_goal(self, state: Grid) -> bool: return state in self._goals

    def actions(self, state: Grid) -> Iterable[Tuple[Tuple[int,int], Tuple[int,int]]]:
        """
        Trả về các hành động hoán đổi: ((r1,c1),(r2,c2)).
        Rule 1: 2 ô kề nhau (ngang/dọc) A+B=9 -> swap (không dính ô trống).
        Rule 2: swap (0,0)<->(2,2) và (0,2)<->(2,0) (không dính ô trống).
        """
        n = 3
        for r in range(n):
            for c in range(n):
                v = state[r][c]
                if v == 0: continue
                if c+1 < n and state[r][c+1] != 0 and v + state[r][c+1] == 9:
                    yield ((r,c),(r,c+1))
                if r+1 < n and state[r+1][c] != 0 and v + state[r+1][c] == 9:
                    yield ((r,c),(r+1,c))
        for (r1,c1),(r2,c2) in [((0,0),(2,2)), ((0,2),(2,0))]:
            if state[r1][c1] != 0 and state[r2][c2] != 0:
                yield ((r1,c1),(r2,c2))

    def result(self, state: Grid, action: Tuple[Tuple[int,int], Tuple[int,int]]) -> Grid:
        (r1,c1),(r2,c2) = action
        s = [list(row) for row in state]
        s[r1][c1], s[r2][c2] = s[r2][c2], s[r1][c1]
        return tuple(tuple(row) for row in s)

    def step_cost(self, state, action, next_state) -> float: return 1.0
