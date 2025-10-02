from __future__ import annotations
from typing import List, Tuple, Iterable

Grid = Tuple[Tuple[int,...], ...]  # 3x3, 0 = blank

class EightPuzzleProblem:
    def __init__(self, initial: Grid, goals: List[Grid]):
        self._initial = initial
        self._goals = set(goals)  # hashable tuples

    def initial_state(self) -> Grid:
        return self._initial

    def is_goal(self, state: Grid) -> bool:
        return state in self._goals

    def actions(self, state: Grid) -> Iterable[Tuple[Tuple[int,int], Tuple[int,int]]]:
        """
        Trả về các hành động dạng hoán đổi: ((r1,c1),(r2,c2)).
        Rule 1: 2 ô kề nhau A,B (không phải ô trống) và A+B=9 -> được swap.
        Rule 2: swap 2 góc chéo (không dính ô trống).
        (Nếu bạn chọn cho phép trượt ô trống cổ điển, hãy bổ sung ở đây và dùng nhất quán.)
        """
        n = 3
        # Adjacent sum-to-9 swaps
        for r in range(n):
            for c in range(n):
                v = state[r][c]
                if v == 0:
                    continue
                # right
                if c+1 < n and state[r][c+1] != 0:
                    w = state[r][c+1]
                    if v + w == 9:
                        yield ((r,c),(r,c+1))
                # down
                if r+1 < n and state[r+1][c] != 0:
                    w = state[r+1][c]
                    if v + w == 9:
                        yield ((r,c),(r+1,c))

        # Diagonal corner swaps
        pairs = [((0,0),(2,2)), ((0,2),(2,0))]
        for (r1,c1),(r2,c2) in pairs:
            if state[r1][c1] != 0 and state[r2][c2] != 0:
                yield ((r1,c1),(r2,c2))

    def result(self, state: Grid, action: Tuple[Tuple[int,int], Tuple[int,int]]) -> Grid:
        (r1,c1),(r2,c2) = action
        s = [list(row) for row in state]
        s[r1][c1], s[r2][c2] = s[r2][c2], s[r1][c1]
        return tuple(tuple(row) for row in s)

    def step_cost(self, state, action, next_state) -> float:
        return 1.0
