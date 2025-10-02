from __future__ import annotations
from typing import List, Tuple, Iterable, NamedTuple

Pos = Tuple[int,int]
Grid = List[str]

class PacmanState(NamedTuple):
    pacman: Pos
    foods: Tuple[Pos, ...]
    pies_ttl: int
    ghosts: Tuple[Pos, ...]
    steps_mod30: int

class PacmanProblem:
    def __init__(self, grid: Grid, start: Pos, foods: List[Pos], exit_pos: Pos):
        self.grid = grid
        self._start = PacmanState(start, tuple(foods), pies_ttl=0, ghosts=tuple(), steps_mod30=0)
        self.exit = exit_pos

    def initial_state(self) -> PacmanState: return self._start
    def is_goal(self, s: PacmanState) -> bool: return len(s.foods)==0 and s.pacman == self.exit
    def actions(self, s: PacmanState) -> Iterable[str]: return ["N","S","E","W"]

    def _can_pass(self, r: int, c: int, pies_ttl: int) -> bool:
        if 0 <= r < len(self.grid) and 0 <= c < len(self.grid[0]):
            if self.grid[r][c] == '%': return pies_ttl > 0
            return True
        return False

    def result(self, s: PacmanState, a: str) -> PacmanState:
        drdc = {"N":(-1,0),"S":(1,0),"W":(0,-1),"E":(0,1)}
        dr, dc = drdc[a]; r, c = s.pacman; nr, nc = r+dr, c+dc
        pies_ttl = max(0, s.pies_ttl - 1)
        if not self._can_pass(nr, nc, s.pies_ttl): nr, nc = r, c
        foods = list(s.foods)
        if (nr, nc) in foods: foods.remove((nr, nc))
        # TODO: xử lý 'O', 'G', teleport ở 4 góc, quay map mỗi 30 bước
        return PacmanState((nr,nc), tuple(foods), pies_ttl, s.ghosts, (s.steps_mod30+1)%30)

    def step_cost(self, s: PacmanState, a: str, s2: PacmanState) -> float: return 1.0
