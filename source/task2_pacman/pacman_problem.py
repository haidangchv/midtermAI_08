# source/task2_pacman/pacman_problem.py
from __future__ import annotations
from typing import List, Tuple, Iterable, NamedTuple, Dict
from functools import lru_cache
from collections import deque

Pos = Tuple[int, int]
Grid = List[str]

# ---------- các hàm quay lưới/toạ độ ----------
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
        r, c = (c, R - 1 - r)
        R, C = C, R
    return (r, c)

# ---------- BFS khoảng cách mê cung (không dùng Euclid/Manhattan) ----------
def _neighbors_grid(g: Grid, r: int, c: int):
    R, C = len(g), len(g[0])
    for dr, dc in [(-1,0),(1,0),(0,-1),(0,1)]:
        nr, nc = r + dr, c + dc
        if 0 <= nr < R and 0 <= nc < C and g[nr][nc] != '%':
            yield nr, nc

def _bfs_maze_dist(g: Grid, src: Pos, dst: Pos) -> int:
    """Khoảng cách ngắn nhất theo lưới (BFS), chặn tường '%'. Trả inf nếu không tới được."""
    if src == dst:
        return 0
    q = deque([src])
    dist: Dict[Pos, int] = {src: 0}
    while q:
        r, c = q.popleft()
        for nr, nc in _neighbors_grid(g, r, c):
            if (nr, nc) in dist:
                continue
            dist[(nr, nc)] = dist[(r, c)] + 1
            if (nr, nc) == dst:
                return dist[(nr, nc)]
            q.append((nr, nc))
    return float("inf")

# ---------- Kiểu state ----------
class Ghost(NamedTuple):
    pos: Pos
    dir: int  # +1 phải, -1 trái (trên hàng)

class PacmanState(NamedTuple):
    pacman: Pos
    foods: Tuple[Pos, ...]
    pies: Tuple[Pos, ...]
    ghosts: Tuple[Ghost, ...]
    ttl: int
    steps_mod30: int
    rot_idx: int

# ---------- Bài toán ----------
class PacmanProblem:
    """
    - Mỗi 30 bước: xoay mê cung 90° CW, biến đổi toạ độ Pacman/foods/pies/ghosts/Exit.
    - Teleport: khi Pacman đứng tại 'ô neo' gần TL/TR/BL/BR (open cell đầu tiên khi quét từ góc),
      có thể nhảy tới neo tương ứng. Action code: TUL/TUR/TBL/TBR, cost=1.
      (ĐÃ CẮT NHÁNH: chỉ thêm teleport khi thực sự rút ngắn đường ≥2 bước tới mục tiêu gần nhất.)
    - Pie 'O': khi ăn -> ttl=5, đi xuyên '%'.
    - Ma: mỗi bước tick ngang 1 ô; đụng tường đảo chiều; nếu hàng kín thì đứng yên.
    - Nếu Pacman đụng ma -> transition invalid (return None) để A* không mở rộng.
    """
    def __init__(self, grid: Grid, start: Pos, foods: List[Pos], exit_pos: Pos,
             pies: List[Pos] = None, ghosts: List[Tuple[Pos, int]] = None,
             ttl0: int = 0, steps_mod30_0: int = 0, rot_idx0: int = 0):
        self.orig_grid = grid
        self.orig_R, self.orig_C = len(grid), len(grid[0])
        self.exit_orig = exit_pos
        self.pies_orig = tuple(pies or [])

        safe_ghosts = []
        for g in (ghosts or []):
            try:
                if isinstance(g, dict):
                    pos = tuple(g.get("pos"))
                    d = int(g.get("dir", +1))
                else:
                    pos, d = g  # kỳ vọng ((r,c), dir) hoặc [(r,c), dir]
                    pos = tuple(pos); d = int(d)
                d = +1 if d not in (-1, +1) else d
                safe_ghosts.append(Ghost(pos, d))
            except Exception:
                # bỏ qua phần tử ghost lỗi thay vì raise
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
        )


    # ---------- helpers ----------
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

    # ----- corner anchors (ô đi được gần 4 góc) -----
    def _first_open_from_top_left(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R):
            for c in range(C):
                if g[r][c] != '%': return (r, c)
        return (0, 0)

    def _first_open_from_top_right(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R):
            for c in range(C-1, -1, -1):
                if g[r][c] != '%': return (r, c)
        return (0, C-1)

    def _first_open_from_bottom_left(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R-1, -1, -1):
            for c in range(C):
                if g[r][c] != '%': return (r, c)
        return (R-1, 0)

    def _first_open_from_bottom_right(self, g: Grid) -> Pos:
        R, C = len(g), len(g[0])
        for r in range(R-1, -1, -1):
            for c in range(C-1, -1, -1):
                if g[r][c] != '%': return (r, c)
        return (R-1, C-1)

    def _corner_anchor_positions(self, rot_idx: int) -> Dict[str, Pos]:
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

    # ----- cache maze distance theo rot_idx -----
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
        """
        Trả về tập action cho trạng thái s.
        - ƯU TIÊN TELEPORT: nếu Pacman đang đứng tại một ô neo (gần TL/TR/BL/BR),
        luôn thêm 4 action teleport và đặt CHÚNG LÊN TRƯỚC để A* thử trước.
        - Không dùng Stop.
        """
        # các hướng di chuyển cơ bản
        move_actions = ["N", "S", "E", "W"]

        # kiểm tra neo hiện tại theo lưới đã xoay
        anchors = self._corner_anchor_positions(s.rot_idx)
        at_anchor = s.pacman in anchors.values()

        if at_anchor:
            # ƯU TIÊN TELEPORT: đưa teleport lên ĐẦU danh sách
            tp_actions = ["TUL", "TUR", "TBL", "TBR"]
            return tp_actions + move_actions

        return move_actions


    def result(self, s: PacmanState, a: str) -> PacmanState | None:
        g = self._current_grid(s.rot_idx)
        R, C = len(g), len(g[0])
        anchors = self._corner_anchor_positions(s.rot_idx)

        r, c = s.pacman
        nr, nc = r, c
        ttl = max(0, s.ttl - 1)

        # move pacman
        if a in ("N", "S", "E", "W"):
            drdc = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
            dr, dc = drdc[a]
            tr, tc = r + dr, c + dc
            if 0 <= tr < R and 0 <= tc < C:
                if g[tr][tc] != '%' or ttl > 0:
                    nr, nc = tr, tc
        elif a in ("TUL", "TUR", "TBL", "TBR"):
            if s.pacman not in anchors.values():
                return None
            nr, nc = anchors[a]
        else:
            return None

        # (MỚI) đụng ma TRƯỚC tick => chết (bỏ điều kiện TTL)
        for gh in s.ghosts:
            if gh.pos == (nr, nc):
                return None

        # ăn food/pie
        foods = list(s.foods)
        if (nr, nc) in foods:
            foods.remove((nr, nc))
        pies = list(s.pies)
        if (nr, nc) in pies:
            pies.remove((nr, nc))
            ttl = 5

        # ghost tick
        old_ghosts = s.ghosts
        ghosts = self._move_ghosts(s.rot_idx, old_ghosts)

        # (MỚI) đụng ma SAU tick + SWAP cạnh => chết
        for gh_old, gh_new in zip(old_ghosts, ghosts):
            if gh_new.pos == (nr, nc):
                return None
            if gh_old.pos == (nr, nc) and gh_new.pos == (r, c):  # swap
                return None

        steps_mod30 = (s.steps_mod30 + 1) % 30
        new_state = PacmanState((nr, nc), tuple(foods), tuple(pies), ghosts, ttl, steps_mod30, s.rot_idx)
        if steps_mod30 == 0:
            new_state = self._rotate_world(new_state)
        return new_state

    def step_cost(self, s: PacmanState, a: str, s2: PacmanState) -> float:
        return 1.0
