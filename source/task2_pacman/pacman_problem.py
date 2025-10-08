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
    - Teleport 4 góc: nếu Pacman đứng ở góc -> dịch chuyển tới góc đối diện theo cặp
        (0,0) <-> (R-1,C-1), (0,C-1) <-> (R-1,0)
    - Ma: di chuyển ngang mỗi bước; nếu đụng tường -> đảo chiều rồi đi 1 bước.
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

    def _teleport_if_corner(self, rot_idx: int, r: int, c: int) -> Pos:
        g = self._current_grid(rot_idx)
        R, C = len(g), len(g[0])
        corners = {(0, 0): (R - 1, C - 1), (0, C - 1): (R - 1, 0), (R - 1, 0): (0, C - 1), (R - 1, C - 1): (0, 0)}
        return corners.get((r, c), (r, c))

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
        # Kích thước hiện tại trước xoay
        cur_R, cur_C = len(self._current_grid(s.rot_idx)), len(self._current_grid(s.rot_idx)[0])

        pac = rot_pos_cw(s.pacman, cur_R, cur_C)
        foods = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.foods)
        pies = tuple(rot_pos_cw(p, cur_R, cur_C) for p in s.pies)
        ghosts = tuple(Ghost(rot_pos_cw(g.pos, cur_R, cur_C), g.dir) for g in s.ghosts)
        # dir: vẫn là +1 sang phải/-1 sang trái trong hệ toạ độ mới (không đổi dấu ở đây)

        return PacmanState(pac, foods, pies, ghosts, s.ttl, s.steps_mod30, rnew)

    # --------------- Problem API ---------------
    def initial_state(self) -> PacmanState:
        return self._start

    def is_goal(self, s: PacmanState) -> bool:
        return len(s.foods) == 0 and s.pacman == self._exit_at(s.rot_idx)

    def actions(self, s: PacmanState) -> Iterable[str]:
        return ["N", "S", "E", "W"]

    def result(self, s: PacmanState, a: str) -> PacmanState | None:
        # Lấy grid hiện tại theo rot_idx
        g = self._current_grid(s.rot_idx)
        R, C = len(g), len(g[0])

        # 1) Pacman move
        drdc = {"N": (-1, 0), "S": (1, 0), "W": (0, -1), "E": (0, 1)}
        dr, dc = drdc[a]
        r, c = s.pacman
        nr, nc = r + dr, c + dc

        # Xuyên tường nếu ttl>0
        if 0 <= nr < R and 0 <= nc < C:
            if self._is_wall(s.rot_idx, nr, nc) and s.ttl <= 0:
                nr, nc = r, c  # đứng yên nếu đụng tường mà không có TTL
        else:
            # đi ra ngoài -> xem như tường
            nr, nc = r, c

        # 2) Teleport nếu đứng ở góc
        tr, tc = self._teleport_if_corner(s.rot_idx, nr, nc)
        nr, nc = tr, tc

        # 3) Ăn food / pie
        foods = list(s.foods)
        if (nr, nc) in foods:
            foods.remove((nr, nc))
        pies = list(s.pies)
        ttl = max(0, s.ttl - 1)
        if (nr, nc) in pies:
            pies.remove((nr, nc))
            ttl = 5

        # 4) Ma di chuyển (theo rot_idx hiện tại)
        ghosts = self._move_ghosts(s.rot_idx, s.ghosts)

        # 5) Va chạm ma? loại trừ trạng thái
        for gh in ghosts:
            if gh.pos == (nr, nc):
                return None  # bị bắt -> coi như transition không hợp lệ

        # 6) Tăng steps_mod30, nếu chẵn 30 -> xoay mê cung
        steps_mod30 = (s.steps_mod30 + 1) % 30
        new_state = PacmanState((nr, nc), tuple(foods), tuple(pies), ghosts, ttl, steps_mod30, s.rot_idx)
        if steps_mod30 == 0:
            new_state = self._rotate_world(new_state)

        return new_state

    def step_cost(self, s: PacmanState, a: str, s2: PacmanState) -> float:
        return 1.0
    
    def heuristic(self, s: PacmanState) -> float:
        """Ước lượng chi phí từ trạng thái s đến trạng thái goal."""
        if not s.foods:
            # chỉ còn mỗi đi đến exit
            ex_r, ex_c = self._exit_at(s.rot_idx)
            p_r, p_c = s.pacman
            return abs(ex_r - p_r) + abs(ex_c - p_c)

        # Ước lượng: tổng khoảng cách từ Pacman đến food gần nhất + từ food đó đến exit
        ex_r, ex_c = self._exit_at(s.rot_idx)
        p_r, p_c = s.pacman
        min_dist = float("inf")
        for (f_r, f_c) in s.foods:
            dist = abs(f_r - p_r) + abs(f_c - p_c) + abs(ex_r - f_r) + abs(ex_c - f_c)
            if dist < min_dist:
                min_dist = dist
        return min_dist