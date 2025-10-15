from __future__ import annotations
from typing import List, Tuple, Iterable, NamedTuple

Pos = Tuple[int,int]
Grid = List[str]

def rotate_grid_cw(grid: Grid) -> Grid:
    R, C = len(grid), len(grid[0])
    return ["".join(grid[R - 1 - r][c] for r in range(R)) for c in range(C)]

def rot_pos_cw(p: Pos, R: int, C: int) -> Pos:
    r, c = p
    return (c, R - 1 - r)

def rotate_many(grid: Grid, k: int) -> Grid:
    g = grid
    for _ in range(k % 4):
        g = rotate_grid_cw(g)
    return g

def rot_pos_many(p: Pos, orig_R: int, orig_C: int, k: int) -> Pos:
    r, c = p
    R, C = orig_R, orig_C
    for _ in range(k % 4):
        (r, c) = (c, R - 1 - r)
        R, C = C, R
    return (r, c)

class Ghost(NamedTuple):
    pos: Pos
    dir: int  # +1: sang phải, -1: sang trái

class PacmanState(NamedTuple):
    pacman: Pos
    foods: Tuple[Pos, ...]
    pies: Tuple[Pos, ...]
    ghosts: Tuple[Ghost, ...]
    ttl: int
    steps_mod30: int
    rot_idx: int

class PacmanProblem:
    """
    - Teleport góc: (0,0)<->(R-1,C-1), (0,C-1)<->(R-1,0)
    - Ăn O -> TTL=5 (xuyên tường)
    - Ma đi ngang; đụng tường đảo chiều
    - Mỗi 30 bước: xoay thế giới 90° CW (P, food, pie, ghost, Exit)
    - Đụng ma -> transition None (bị loại)
    """
    def __init__(self, 
                 grid: Grid, 
                 start: Pos, 
                 foods: List[Pos], 
                 exit_pos: Pos,
                 pies: List[Pos] = None, 
                 ghosts: List[Tuple[Pos, int]] = None):
        self.orig_grid = grid
        self.orig_R, self.orig_C = len(grid), len(grid[0])
        self.exit_orig = exit_pos
        self.pies_orig = tuple(pies or [])
        self.ghosts_orig = tuple(Ghost(p, d) for (p, d) in (ghosts or []))

        self._start = PacmanState(
            pacman=start,
            foods=tuple(foods),
            pies=self.pies_orig,
            ghosts=self.ghosts_orig,
            ttl=0,
            steps_mod30=0,
            rot_idx=0,
        )

    # ------- helpers -------
    def _current_grid(self, rot_idx: int) -> Grid:
        return rotate_many(self.orig_grid, rot_idx)

    def _exit_at(self, rot_idx: int) -> Pos:
        return rot_pos_many(self.exit_orig, self.orig_R, self.orig_C, rot_idx)

    def _is_wall(self, rot_idx: int, r: int, c: int) -> bool:
        g = self._current_grid(rot_idx)
        R, C = len(g), len(g[0])
        if 0 <= r < R and 0 <= c < C:
            return g[r][c] == '%'
        return True

    def _teleport_if_corner(self, rot_idx: int, r: int, c: int) -> Pos:
        g = self._current_grid(rot_idx)
        R, C = len(g), len(g[0])
        corners = {(0, 0): (R - 1, C - 1), (0, C - 1): (R - 1, 0),
                   (R - 1, 0): (0, C - 1), (R - 1, C - 1): (0, 0)}
        return corners.get((r, c), (r, c))

    def _move_ghosts(self, rot_idx: int, ghosts: Tuple[Ghost, ...]) -> Tuple[Ghost, ...]:
        g = self._current_grid(rot_idx)
        R, C = len(g), len(g[0])
        out = []
        for gh in ghosts:
            r, c = gh.pos
            d = gh.dir
            nc = c + d
            if not (0 <= r < R and 0 <= nc < C) or g[r][nc] == '%':
                d = -d
                nc = c + d
                if not (0 <= r < R and 0 <= nc < C) or g[r][nc] == '%':
                    out.append(Ghost((r, c), d))
                    continue
            out.append(Ghost((r, nc), d))
        return tuple(out)

    def _rotate_world(self, s: PacmanState) -> PacmanState:
        rnew = (s.rot_idx + 1) % 4
        cur_R, cur_C = len(self._current_grid(s.rot_idx)), len(self._current_grid(s.rot_idx)[0])

        pac = rot_pos_cw(s.pacman, cur_R, cur_C)
        foods = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.foods)
        pies = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.pies)
        ghosts = tuple(Ghost(rot_pos_cw(g.pos, cur_R, cur_C), g.dir) for g in s.ghosts)

        return PacmanState(pac, foods, pies, ghosts, s.ttl, s.steps_mod30, rnew)

    # ------- Problem API -------
    def initial_state(self) -> PacmanState: 
        return self._start

    def is_goal(self, s: PacmanState) -> bool:
        return len(s.foods)==0 and s.pacman == self._exit_at(s.rot_idx)

    def actions(self, s: PacmanState) -> Iterable[str]:
        return ["N","S","E","W"]

    def result(self, s: PacmanState, a: str) -> PacmanState | None:
        g = self._current_grid(s.rot_idx)
        R, C = len(g), len(g[0])

        drdc = {"N":(-1,0),"S":(1,0),"W":(0,-1),"E":(0,1)}
        dr, dc = drdc[a]; r, c = s.pacman; nr, nc = r+dr, c+dc

        # xuyên tường nếu TTL>0
        if 0 <= nr < R and 0 <= nc < C:
            if self._is_wall(s.rot_idx, nr, nc) and s.ttl <= 0:
                nr, nc = r, c
        else:
            nr, nc = r, c

        # teleport góc
        nr, nc = self._teleport_if_corner(s.rot_idx, nr, nc)

        # ăn food/pie
        foods = list(s.foods)
        if (nr, nc) in foods:
            foods.remove((nr, nc))
        pies = list(s.pies)
        ttl = max(0, s.ttl - 1)
        if (nr, nc) in pies:
            pies.remove((nr, nc))
            ttl = 5

        # ma di chuyển
        ghosts = self._move_ghosts(s.rot_idx, s.ghosts)

        # va chạm ma -> None
        for gh in ghosts:
            if gh.pos == (nr, nc):
                return None

        # tăng bước + xoay mỗi 30
        steps_mod30 = (s.steps_mod30 + 1) % 30
        new_state = PacmanState((nr,nc), tuple(foods), tuple(pies), ghosts, ttl, steps_mod30, s.rot_idx)
        if steps_mod30 == 0:
            new_state = self._rotate_world(new_state)

        return new_state

    def step_cost(self, s: PacmanState, a: str, s2: PacmanState) -> float:
        return 1.0
