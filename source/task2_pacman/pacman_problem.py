from __future__ import annotations
from typing import List, Tuple, Iterable, NamedTuple, Dict
from functools import lru_cache
from collections import deque

Pos = Tuple[int, int]
Grid = List[str]

# ---------- quay lưới/toạ độ ----------
def rotate_grid_cw(grid: Grid) -> Grid:
    R, C = len(grid), len(grid[0])
    return ["".join(grid[R - 1 - r][c] for r in range(R)) for c in range(C)]

def rot_pos_cw(p: Pos, R: int, C: int) -> Pos:
    r, c = p
    return (c, R - 1 - r)

def rotate_many(grid: Grid, k: int) -> Grid:
    k %= 4
    g = grid
    for _ in range(k):
        g = rotate_grid_cw(g)
    return g

def rot_pos_many(p: Pos, R: int, C: int, k: int) -> Pos:
    k %= 4
    rr, cc = R, C
    r, c = p
    for _ in range(k):
        r, c = rot_pos_cw((r, c), rr, cc)
        rr, cc = cc, rr
    return (r, c)

# ---------- BFS khoảng cách mê cung ----------
def _neighbors_grid(g: Grid, r: int, c: int):
    R, C = len(g), len(g[0])
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < R and 0 <= nc < C and g[nr][nc] != '%':
            yield (nr, nc)

def _bfs_maze_dist(g: Grid, src: Pos, dst: Pos) -> int:
    if src == dst:
        return 0
    R, C = len(g), len(g[0])
    dq = deque([src])
    dist = {src: 0}
    while dq:
        r, c = dq.popleft()
        for nr, nc in _neighbors_grid(g, r, c):
            if (nr, nc) not in dist:
                dist[(nr, nc)] = dist[(r, c)] + 1
                if (nr, nc) == dst:
                    return dist[(nr, nc)]
                dq.append((nr, nc))
    return 10**9

# ---------- Ma ----------
class Ghost(NamedTuple):
    pos: Pos
    dir: int 

class PacmanState(NamedTuple):
    pacman: Pos
    foods: Tuple[Pos, ...]
    pies: Tuple[Pos, ...]
    ghosts: Tuple[Ghost, ...]
    ttl: int
    steps_mod30: int
    rot_idx: int
    destroyed: Tuple[Pos, ...]  # các ô tường đã bị ăn 

# ---------- Bài toán ----------
class PacmanProblem:
    def __init__(self, grid: Grid, start: Pos, foods: List[Pos], exit_pos: Pos,
                 pies: List[Pos] = None, ghosts: List[Tuple[Pos, int]] = None,
                 ttl0: int = 0, steps_mod30_0: int = 0, rot_idx0: int = 0):
        self.orig_grid = grid
        self.orig_R, self.orig_C = len(grid), len(grid[0])
        self.exit_orig = exit_pos
        self.pies_orig = tuple(pies or [])

        # sanitize ghosts
        safe_ghosts = []
        for g in (ghosts or []):
            try:
                if isinstance(g, dict):
                    pos = tuple(g.get("pos"))
                    d = int(g.get("dir", +1))
                else:
                    pos, d = g
                    pos = tuple(pos); d = int(d)
                d = +1 if d not in (-1, +1) else d
                safe_ghosts.append(Ghost(pos, d))
            except Exception:
                continue
        self.ghosts_orig = tuple(safe_ghosts)

        self._start = PacmanState(
            pacman=start,
            foods=tuple(foods),
            pies=self.pies_orig,
            ghosts=self.ghosts_orig,
            ttl=ttl0,
            steps_mod30=steps_mod30_0 % 30,
            rot_idx=rot_idx0 % 4,
            destroyed=tuple(),   # ban đầu chưa phá tường nào
        )

    # ---------- helpers ----------
    def _current_grid(self, rot_idx: int) -> Grid:
        return rotate_many(self.orig_grid, rot_idx)

    def _exit_at(self, rot_idx: int) -> Pos:
        return rot_pos_many(self.exit_orig, self.orig_R, self.orig_C, rot_idx)

    def _apply_destruction(self, g: Grid, destroyed: Tuple[Pos, ...]) -> Grid:
        if not destroyed:
            return g
        rows = [list(row) for row in g]
        R, C = len(g), len(g[0])
        for (r, c) in destroyed:
            if 0 <= r < R and 0 <= c < C and rows[r][c] == '%':
                rows[r][c] = ' '
        return ["".join(row) for row in rows]

    def _grid_with_destruction(self, s: PacmanState) -> Grid:
        g = self._current_grid(s.rot_idx)
        return self._apply_destruction(g, s.destroyed)

    def _corner_anchor_positions(self, arg) -> Dict[str, Pos]:
        if isinstance(arg, int):
            rot_idx = arg
            g = self._current_grid(rot_idx)
        else:
            s = arg
            g = self._grid_with_destruction(s)
        R, C = len(g), len(g[0])

        def first_open_from_top_left():
            for r in range(R):
                for c in range(C):
                    if g[r][c] != '%':
                        return (r, c)
            return (0, 0)

        def first_open_from_top_right():
            for r in range(R):
                for c in range(C-1, -1, -1):
                    if g[r][c] != '%':
                        return (r, c)
            return (0, C-1)

        def first_open_from_bottom_left():
            for r in range(R-1, -1, -1):
                for c in range(C):
                    if g[r][c] != '%':
                        return (r, c)
            return (R-1, 0)

        def first_open_from_bottom_right():
            for r in range(R-1, -1, -1):
                for c in range(C-1, -1, -1):
                    if g[r][c] != '%':
                        return (r, c)
            return (R-1, C-1)

        return {
            "TUL": first_open_from_top_left(),
            "TUR": first_open_from_top_right(),
            "TBL": first_open_from_bottom_left(),
            "TBR": first_open_from_bottom_right(),
        }

    # cache 
    @lru_cache(maxsize=100_000)
    def _maze_dist_cached(self, rot_idx: int, src: Pos, dst: Pos) -> int:
        g = self._current_grid(rot_idx)
        return _bfs_maze_dist(g, src, dst)

    # ---------- API ----------
    def initial_state(self) -> PacmanState:
        return self._start

    def is_goal(self, s: PacmanState) -> bool:
        return len(s.foods) == 0 and s.pacman == self._exit_at(s.rot_idx)

    def actions(self, s: PacmanState) -> Iterable[str]:
        move_actions = ["N", "S", "E", "W"]
        anchors = self._corner_anchor_positions(s)
        at_anchor = s.pacman in anchors.values()
        if at_anchor:
            return ["TUL", "TUR", "TBL", "TBR"] + move_actions
        return move_actions

    def _move_ghosts_dyn(self, s: PacmanState) -> Tuple[Ghost, ...]:
        g = self._grid_with_destruction(s)
        R, C = len(g), len(g[0])
        out = []
        for gh in s.ghosts:
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
        destroyed = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.destroyed)

        return PacmanState(pac, foods, pies, ghosts, s.ttl, s.steps_mod30, rnew, destroyed)

    # ---------- transition ----------
    def result(self, s: PacmanState, a: str) -> PacmanState | None:
        g = self._grid_with_destruction(s)
        R, C = len(g), len(g[0])
        anchors = self._corner_anchor_positions(s)

        r, c = s.pacman
        nr, nc = r, c
        ttl = max(0, s.ttl - 1)
        destroyed = set(s.destroyed)

        # 1) Di chuyển Pacman (ăn tường nếu ttl>0)
        if a in ("N", "S", "E", "W"):
            drdc = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
            dr, dc = drdc[a]
            tr, tc = r + dr, c + dc
            if not (0 <= tr < R and 0 <= tc < C):
                return None
            if g[tr][tc] == '%':
                if ttl > 0:
                    destroyed.add((tr, tc))  # ăn tường: xoá vĩnh viễn
                else:
                    return None
            nr, nc = tr, tc

        elif a in ("TUL", "TUR", "TBL", "TBR"):
            if s.pacman not in anchors.values():
                return None
            nr, nc = anchors[a]
        else:
            return None

        # 2) Va chạm 
        if ttl == 0:
            for gh in s.ghosts:
                if gh.pos == (nr, nc):
                    return None

        # 3) Ăn food/pie
        foods = list(s.foods)
        if (nr, nc) in foods:
            foods.remove((nr, nc))
        pies = list(s.pies)
        if (nr, nc) in pies:
            pies.remove((nr, nc))
            ttl = 6

        # 4) Ma di chuyển 
        old_ghosts = s.ghosts
        ghosts = self._move_ghosts_dyn(PacmanState((nr, nc), tuple(foods), tuple(pies), s.ghosts, ttl, s.steps_mod30, s.rot_idx, tuple(destroyed)))

        # 5) Va chạm SAU tick + GIAO CẮT CẠNH (swap)
        for gh_old, gh_new in zip(old_ghosts, ghosts):
            if gh_new.pos == (nr, nc):
                return None
            if gh_old.pos == (nr, nc) and gh_new.pos == (r, c):
                return None

        # 6) Tick xoay mỗi 30 bước
        steps_mod30 = (s.steps_mod30 + 1) % 30
        new_state = PacmanState((nr, nc), tuple(foods), tuple(pies), ghosts, ttl, steps_mod30, s.rot_idx, tuple(destroyed))
        if steps_mod30 == 0:
            new_state = self._rotate_world(new_state)
        return new_state

    def step_cost(self, s: PacmanState, a: str, s2: PacmanState) -> float:
        return 1.0
