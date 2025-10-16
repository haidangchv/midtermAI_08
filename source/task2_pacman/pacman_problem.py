# source/task2_pacman/pacman_problem.py
from __future__ import annotations
from typing import List, Tuple, Iterable, NamedTuple

Pos = Tuple[int, int]
Grid = List[str]

def rotate_grid_cw(grid: Grid) -> Grid:
    R, C = len(grid), len(grid[0])
    return ["".join(grid[R - 1 - r][c] for r in range(R)) for c in range(C)]

def rot_pos_cw(p: Pos, R: int, C: int) -> Pos:
    # 90° CW: (r, c) -> (c, R-1-r)
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
    dir: int  # +1: sang phải, -1: sang trái (trên hàng hiện tại)

class PacmanState(NamedTuple):
    pacman: Pos
    foods: Tuple[Pos, ...]
    pies: Tuple[Pos, ...]
    ghosts: Tuple[Ghost, ...]  # ma chỉ đi ngang, dội tường
    ttl: int                   # time-to-live xuyên tường (sau khi ăn 'O')
    steps_mod30: int           # đếm bước để xoay mê cung
    rot_idx: int               # số lần xoay 90° CW đã áp dụng (0..3)

class PacmanProblem:
    """
    - Mỗi 30 bước: xoay mê cung 90° CW, đồng thời biến đổi toạ độ của Pacman/food/pies/ghosts/Exit.
    - Teleport 4 góc: nếu Pacman đứng ở **ô neo** (ô đi được gần mỗi góc nhất),
      thì có thể thực hiện 1 action teleport đến **bất kỳ** ô neo góc khác (TUL/TUR/TBL/TBR).
    - Ma: di chuyển ngang mỗi bước (mô phỏng trong Problem); GUI có thể chạy timer riêng nhưng Problem vẫn hợp lệ.
    - Đụng ma => chuyển trạng thái bị chặn (return None) để BFS/A* không mở rộng.
    """
    def __init__(self, grid: Grid, start: Pos, foods: List[Pos], exit_pos: Pos,
                 pies: List[Pos] = None, ghosts: List[Tuple[Pos, int]] = None):
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

    # ---------------- helpers ----------------
    def _current_grid(self, rot_idx: int) -> Grid:
        return rotate_many(self.orig_grid, rot_idx)

    def _exit_at(self, rot_idx: int) -> Pos:
        return rot_pos_many(self.exit_orig, self.orig_R, self.orig_C, rot_idx)

    def _is_wall(self, rot_idx: int, r: int, c: int) -> bool:
        g = self._current_grid(rot_idx)
        R, C = len(g), len(g[0])
        if 0 <= r < R and 0 <= c < C:
            return g[r][c] == '%'
        return True  # ra ngoài = như tường

    # ---- tìm ô neo (ô đi được gần mỗi góc nhất) ----
    def _first_open_from_top_left(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R):
            for c in range(C):
                if g[r][c] != '%':
                    return (r, c)
        return (0, 0)

    def _first_open_from_top_right(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R):
            for c in range(C - 1, -1, -1):
                if g[r][c] != '%':
                    return (r, c)
        return (0, C - 1)

    def _first_open_from_bottom_left(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R - 1, -1, -1):
            for c in range(C):
                if g[r][c] != '%':
                    return (r, c)
        return (R - 1, 0)

    def _first_open_from_bottom_right(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R - 1, -1, -1):
            for c in range(C - 1, -1, -1):
                if g[r][c] != '%':
                    return (r, c)
        return (R - 1, C - 1)

    def _corner_anchor_positions(self, rot_idx: int):
        """Trả về 4 ô neo (đi được) gần TL/TR/BL/BR nhất của grid hiện tại."""
        g = self._current_grid(rot_idx)
        return {
            "TUL": self._first_open_from_top_left(g),
            "TUR": self._first_open_from_top_right(g),
            "TBL": self._first_open_from_bottom_left(g),
            "TBR": self._first_open_from_bottom_right(g),
        }

    def _move_ghosts(self, rot_idx: int, ghosts: Tuple[Ghost, ...]) -> Tuple[Ghost, ...]:
        g = self._current_grid(rot_idx)
        R, C = len(g), len(g[0])
        out = []
        for gh in ghosts:
            r, c = gh.pos
            d = gh.dir
            nc = c + d
            # va tường? -> đảo chiều và bước 1 ô
            if not (0 <= r < R and 0 <= nc < C) or g[r][nc] == '%':
                d = -d
                nc = c + d
                # nếu vẫn tường (hàng bị kín), đứng yên
                if not (0 <= r < R and 0 <= nc < C) or g[r][nc] == '%':
                    out.append(Ghost((r, c), d))
                    continue
            out.append(Ghost((r, nc), d))
        return tuple(out)

    def _rotate_world(self, s: PacmanState) -> PacmanState:
        """Xoay mê cung + biến đổi tất cả toạ độ 90° CW"""
        rnew = (s.rot_idx + 1) % 4
        cur_R, cur_C = len(self._current_grid(s.rot_idx)), len(self._current_grid(s.rot_idx)[0])

        pac = rot_pos_cw(s.pacman, cur_R, cur_C)
        foods = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.foods)
        pies = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.pies)
        ghosts = tuple(Ghost(rot_pos_cw(g.pos, cur_R, cur_C), g.dir) for g in s.ghosts)

        return PacmanState(pac, foods, pies, ghosts, s.ttl, s.steps_mod30, rnew)

    # --------------- Problem API ---------------
    def initial_state(self) -> PacmanState:
        return self._start

    def is_goal(self, s: PacmanState) -> bool:
        return len(s.foods) == 0 and s.pacman == self._exit_at(s.rot_idx)

    def actions(self, s: PacmanState) -> Iterable[str]:
        base = ["N", "S", "E", "W"]
        anchors = self._corner_anchor_positions(s.rot_idx)
        # nếu đang ở một ô neo -> có thêm 4 action teleport
        if s.pacman in anchors.values():
            return base + ["TUL", "TUR", "TBL", "TBR"]
        return base

    def result(self, s: PacmanState, a: str) -> PacmanState | None:
        g = self._current_grid(s.rot_idx)
        R, C = len(g), len(g[0])
        anchors = self._corner_anchor_positions(s.rot_idx)

        r, c = s.pacman
        nr, nc = r, c
        ttl = max(0, s.ttl - 1)

        if a in ("N", "S", "E", "W"):
            drdc = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
            dr, dc = drdc[a]
            tr, tc = r + dr, c + dc
            # di chuyển thường: bị tường thì đứng yên (trừ khi TTL>0)
            if 0 <= tr < R and 0 <= tc < C:
                if g[tr][tc] != '%' or ttl > 0:
                    nr, nc = tr, tc
            # ra ngoài lưới coi như tường -> đứng yên

        elif a in ("TUL", "TUR", "TBL", "TBR"):
            # chỉ hợp lệ nếu ĐANG đứng ở MỘT ô neo
            if s.pacman not in anchors.values():
                return None
            nr, nc = anchors[a]

        else:
            return None  # action lạ

        # ăn food/pie
        foods = list(s.foods)
        if (nr, nc) in foods:
            foods.remove((nr, nc))
        pies = list(s.pies)
        if (nr, nc) in pies:
            pies.remove((nr, nc))
            ttl = 5

        # ma di chuyển
        ghosts = self._move_ghosts(s.rot_idx, s.ghosts)

        # va chạm ma? loại trừ trạng thái
        for gh in ghosts:
            if gh.pos == (nr, nc):
                return None  # bị bắt -> coi như transition không hợp lệ

        # tăng steps_mod30, nếu chẵn 30 -> xoay mê cung
        steps_mod30 = (s.steps_mod30 + 1) % 30
        new_state = PacmanState((nr, nc), tuple(foods), tuple(pies),
                                ghosts, ttl, steps_mod30, s.rot_idx)
        if steps_mod30 == 0:
            new_state = self._rotate_world(new_state)

        return new_state

    def step_cost(self, s: PacmanState, a: str, s2: PacmanState) -> float:
        return 1.0
