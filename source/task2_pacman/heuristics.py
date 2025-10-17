# source/task2_pacman/heuristics.py

from functools import lru_cache
from collections import deque

# ----------------- Khoảng cách mê cung (BFS) -----------------
def _neighbors(g, r, c):
    R, C = len(g), len(g[0])
    for dr, dc in [(-1,0), (1,0), (0,-1), (0,1)]:
        nr, nc = r+dr, c+dc
        if 0 <= nr < R and 0 <= nc < C and g[nr][nc] != '%':
            yield nr, nc

def _bfs_dist(g, src, dst):
    if src == dst:
        return 0
    q = deque([src])
    dist = {src: 0}
    while q:
        r, c = q.popleft()
        for nr, nc in _neighbors(g, r, c):
            if (nr, nc) in dist:
                continue
            dist[(nr, nc)] = dist[(r, c)] + 1
            if (nr, nc) == dst:
                return dist[(nr, nc)]
            q.append((nr, nc))
    # không tới được
    return 10**9

# ----------------- Heuristic biết teleport -----------------
class HeuristicTeleportAware:
    """
    h(s) ưu tiên đồ ăn (food) gần teleport:
      - Nếu chưa ăn hết food:
            h(s) = min_T( dist_T(pac, food) ) + MST( foods ∪ {exit} )  (MST dùng dist thường)
      - Nếu hết food:
            h(s) = dist_T(pac, exit)

    Với dist_T(p, q) = min(
        dist_maze(p, q),
        min_{a ∈ anchors} [ dist_maze(p, a) + jump_cost + dist_maze(a, q) ]
    )

    Ghi chú:
      - `jump_cost` mình để = 0 để phản ánh đúng mong muốn “nếu qua teleport còn 12 ô thì lấy 12”
        => heuristic hơi “lạc quan” hơn chi phí thật (vốn nhảy tốn 1 bước), nhưng vẫn admissible.
      - Nếu bạn muốn sát chi phí thật hơn, đổi jump_cost = 1 là xong.
    """

    def __init__(self, problem):
        self.problem = problem

        @lru_cache(maxsize=None)
        def grid_at(rot_idx: int):
            return self.problem._current_grid(rot_idx)
        self._grid_at = grid_at

        @lru_cache(maxsize=None)
        def dist_cache(rot_idx: int, p: tuple, q: tuple):
            g = self._grid_at(rot_idx)
            return _bfs_dist(g, p, q)
        self._dist = dist_cache

    def _teleport_equiv(self, rot_idx: int, p: tuple, q: tuple,
                        anchor_jump_cost: int = 0, jump_cost=None, **_):
        """
        Khoảng cách 'teleport-equivalent' (coi mọi neo teleport là đồng nhất):
        d(p,q) = min(
            dist_maze(p,q),
            min_a dist(p,a) + anchor_jump_cost + min_b dist(b,q)
        )
        - anchor_jump_cost: chi phí nhảy giữa các neo trong HEURISTIC (mặc định 0 theo yêu cầu).
        - jump_cost: tham số tương thích ngược; nếu được truyền thì dùng thay cho anchor_jump_cost.
        """
        if jump_cost is not None:
            anchor_jump_cost = jump_cost  # tương thích ngược

        best = self._dist(rot_idx, p, q)  # đi thường
        anchors = tuple(self.problem._corner_anchor_positions(rot_idx).values())
        if not anchors:
            return best

        to_anchor   = min(self._dist(rot_idx, p, a) for a in anchors)
        from_anchor = min(self._dist(rot_idx, b, q) for b in anchors)
        via_anchors = to_anchor + anchor_jump_cost + from_anchor
        return min(best, via_anchors)


    def _mst_len(self, rot_idx: int, points: set[tuple]):
        pts = list(points)
        if len(pts) <= 1:
            return 0
        used = {pts[0]}
        total = 0
        while len(used) < len(pts):
            best = 10**9
            pick = None
            for u in list(used):
                for v in pts:
                    if v in used:
                        continue
                    # dùng khoảng cách teleport-equivalent (neo đồng nhất)
                    d = self._teleport_equiv(rot_idx, u, v, 0)
                    if d < best:
                        best = d
                        pick = v
            total += best
            used.add(pick)
        return total


    def h(self, s):
        # state fields do PacmanProblem tạo
        rot = s.rot_idx
        pac = s.pacman
        ex  = self.problem._exit_at(rot)
        foods = tuple(s.foods)

        if not foods:
            # chỉ còn ra cửa
            return self._teleport_equiv(rot, pac, ex, 0)

        # Pac -> food gần nhất (có xét teleport)
        dmin = min(self._teleport_equiv(rot, pac, f, 0) for f in foods)
        # MST phần còn lại (foods ∪ {exit}) dùng dist thường
        mst = self._mst_len(rot, set(foods) | {ex})
        return dmin + mst
    def _teleport_aware(self, rot_idx: int, p: tuple, q: tuple, jump_cost: int = 0, **kwargs):
        """Wrapper tương thích tên cũ."""
        return self._teleport_equiv(rot_idx, p, q, jump_cost)

# Heuristic đơn giản để test
class HeuristicZero:
    def h(self, s): return 0
