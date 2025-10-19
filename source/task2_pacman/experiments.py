# source/task2_pacman/experiments.py
from __future__ import annotations
import os, sys, argparse, time, glob
from dataclasses import dataclass

# ==== PATH ====
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))
TASK2_DIR = BASE_DIR
REPO_ROOT = os.path.abspath(os.path.join(TASK2_DIR, "..", ".."))
if TASK2_DIR not in sys.path:
    sys.path.insert(0, TASK2_DIR)

# ==== PROJECT IMPORTS ====
from pacman_problem import PacmanProblem, rotate_many, rot_pos_many
from heuristics import HeuristicPacmanMST
from astar import astar

# ==== I/O LAYOUT ====
def load_layout_file(path: str):
    with open(path, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip("\n")]
    w = max(len(x) for x in lines)
    return [row.ljust(w) for row in lines]

def parse_layout(grid):
    start = None
    foods, pies, ghosts = set(), set(), []
    exit_pos = None
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch == 'P': start = (r, c)
            elif ch == '.': foods.add((r, c))
            elif ch == 'O': pies.add((r, c))
            elif ch == 'E': exit_pos = (r, c)
            elif ch == 'G': ghosts.append(((r, c), +1))  # mặc định mọi ghost dir=+1 (bạn xác nhận ok)
    if start is None or exit_pos is None:
        raise ValueError("Layout cần có 'P' (start) và 'E' (exit).")
    return start, sorted(list(foods)), exit_pos, sorted(list(pies)), ghosts

def resolve_layouts(arg_path: str | None):
    if arg_path:
        if os.path.isfile(arg_path):  return [arg_path]
        if os.path.isdir(arg_path):   return sorted(glob.glob(os.path.join(arg_path, "*.txt")))
        matches = sorted(glob.glob(arg_path))
        if matches: return matches
    # fallback
    filename = "task02_pacman_example_map.txt"
    candidates = [
        os.path.join(REPO_ROOT, "input", filename),
        os.path.join(TASK2_DIR, "input", filename),
        os.path.join(REPO_ROOT, filename),
        os.path.join(TASK2_DIR, filename),
        os.path.join(os.path.dirname(__file__), filename),
    ]
    for p in candidates:
        if os.path.isfile(p):
            return [p]
    raise FileNotFoundError("Không tìm thấy layout. Dùng --layout <file|folder|pattern>.")

# ==== ASTAR WRAPPER ====
def _run_astar(prob, hz, goal_fn=None, max_expanded=0):
    try:
        return astar(prob, hz, graph_search=True, goal_fn=goal_fn, max_expanded=max_expanded)
    except TypeError:
        try:
            return astar(prob, hz, graph_search=True, goal_fn=goal_fn)
        except TypeError:
            try:
                return astar(prob, hz, graph_search=True, max_expanded=max_expanded)
            except TypeError:
                return astar(prob, hz, graph_search=True)

# ==== METRICS ====
@dataclass
class RunMetrics:
    cost: float = 0.0
    expanded: int = 0
    generated: int = 0
    time_ms: float = 0.0

def _safe(res, key, default=0):
    return res.get(key, default) if isinstance(res, dict) else default

# ==== GRID MUTATION (bắt chước game): quay lưới & xoá tường đã ăn ====
def apply_destructions_to_grid(grid, destroyed):
    """Đổi '%' thành ' ' tại các toạ độ trong lưới hiện tại (đã xoay)."""
    if not destroyed:
        return grid
    rows = [list(row) for row in grid]
    R, C = len(rows), len(rows[0])
    for (r, c) in destroyed:
        if 0 <= r < R and 0 <= c < C and rows[r][c] == '%':
            rows[r][c] = ' '
    return ["".join(row) for row in rows]

# ==== CHẠY PER-FOOD THEO ĐÚNG PLAN_ONE_GOAL ====
def run_per_food_like_plan(grid0, start0, foods0, exit0, pies0, ghosts0, max_expanded: int) -> RunMetrics:
    grid_cur = [row[:] for row in grid0]
    R_cur, C_cur = len(grid_cur), len(grid_cur[0])

    cur_pac    = tuple(start0)
    cur_foods  = list(foods0)
    cur_pies   = list(pies0)
    cur_ghosts = [(tuple(pos), d) for (pos, d) in ghosts0]
    cur_exit   = tuple(exit0)

    cur_ttl    = 0
    cur_step   = 0

    total_cost = 0.0
    total_expanded = 0
    total_generated = 0
    total_time_ms = 0.0

    # ---- helper chạy 1 lần A* từ grid_cur với rot_idx0=0 ----
    def _astar_once_eat_one():
        target_after = len(cur_foods) - 1
        def goal_one_food(s, target_count=target_after):
            return (s is not None) and (len(s.foods) == target_count)
        prob = PacmanProblem(grid_cur, cur_pac, cur_foods, cur_exit,
                             pies=cur_pies, ghosts=cur_ghosts,
                             ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
        hz = HeuristicPacmanMST(prob)
        return _run_astar(prob, hz, goal_fn=goal_one_food, max_expanded=max_expanded)

    def _apply_post_segment(last_state):
        """Sau mỗi chặng: quay lưới và xoá tường theo last.rot_idx / last.destroyed."""
        nonlocal grid_cur, R_cur, C_cur
        k = int(last_state.rot_idx) % 4
        if k != 0:
            # quay lưới hiện tại k lần CW
            grid_cur = rotate_many(grid_cur, k)
            # cập nhật kích thước
            R_cur, C_cur = len(grid_cur), len(grid_cur[0])
        # xoá tường đã phá trong chặng vừa qua (toạ độ đã ở hệ toạ độ sau quay k)
        grid_cur = apply_destructions_to_grid(grid_cur, last_state.destroyed)

    # ---- vòng ăn từng food ----
    while len(cur_foods) > 0:
        t0 = time.perf_counter()
        res = _astar_once_eat_one()
        dt = (time.perf_counter() - t0) * 1000.0

        total_time_ms += dt
        if not res or not res.get("solution"):
            break  # không ăn thêm được food nào nữa

        total_cost     += float(_safe(res, "cost", 0.0))
        total_expanded += int(_safe(res, "expanded", 0))
        total_generated+= int(_safe(res, "generated", 0))
        last = res["solution"][-1]
        # cập nhật state cho chặng sau (toạ độ đã phù hợp với grid_cur sau _apply_post_segment)
        cur_pac    = last.pacman
        cur_foods  = list(last.foods)
        cur_pies   = list(last.pies)
        cur_ghosts = [(g.pos, g.dir) for g in last.ghosts]
        cur_ttl    = last.ttl
        cur_step   = last.steps_mod30

        # LƯU Ý QUAN TRỌNG: cập nhật lưới cho chặng sau
        _apply_post_segment(last)

        # cập nhật exit theo lần quay k (nếu có)
        # (cur_exit đang ở hệ toạ độ của grid_cur trước khi quay; sau khi quay k, map đổi hệ toạ độ)
        if last.rot_idx % 4 != 0:
            prev_R, prev_C = R_cur, C_cur 
            if (last.rot_idx % 2) == 1:
                prev_R, prev_C = C_cur, R_cur
            else:
                prev_R, prev_C = R_cur, C_cur
            cur_exit = rot_pos_many(cur_exit, prev_R, prev_C, last.rot_idx % 4)

    # ---- khi hết food: A* tới exit (vẫn theo cơ chế plan) ----
    # chạy 1 phát cuối từ grid_cur hiện tại, rot_idx0=0
    prob = PacmanProblem(grid_cur, cur_pac, cur_foods, cur_exit,
                         pies=cur_pies, ghosts=cur_ghosts,
                         ttl0=cur_ttl, steps_mod30_0=cur_step, rot_idx0=0)
    hz = HeuristicPacmanMST(prob)
    t0 = time.perf_counter()
    res = _run_astar(prob, hz, goal_fn=None, max_expanded=max_expanded)
    dt = (time.perf_counter() - t0) * 1000.0
    total_time_ms += dt

    if res and res.get("solution"):
        total_cost     += float(_safe(res, "cost", 0.0))
        total_expanded += int(_safe(res, "expanded", 0))
        total_generated+= int(_safe(res, "generated", 0))
    return RunMetrics(cost=total_cost, expanded=total_expanded,
                      generated=total_generated,
                      time_ms=total_time_ms)

# ==== OUTPUT ====
OUTPUT_DIR = os.path.join(TASK2_DIR, "output")
TXT_PATH   = os.path.join(OUTPUT_DIR, "experiments_report.txt")


def write_files(layout_path: str, m: RunMetrics):
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    # TXT (overwrite) — simplified metrics output
    with open(TXT_PATH, "w", encoding="utf-8") as f:
        f.write(
            f"cost={m.cost:.0f} | "
            f"expanded={m.expanded} | "
            f"generated={m.generated} | "
            f"time={m.time_ms:.1f}ms\n"
        )
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default="", help="File | folder | glob pattern (.txt).")
    ap.add_argument("--max-expanded", type=int, default=200000, help="Giới hạn số node expand của mỗi lần A*.")
    args = ap.parse_args()

    layouts = resolve_layouts(args.layout)
    for lay in layouts:
        grid = load_layout_file(lay)
        start, foods, exit_pos, pies, ghosts = parse_layout(grid)
        print(f"\n=== LAYOUT: {lay} ===")
        print(f"Grid: {len(grid)}x{len(grid[0])} | foods={len(foods)} pies={len(pies)} ghosts={len(ghosts)}")
        print(f"algo=A*-MST | max_expanded={args.max_expanded}")
        met = run_per_food_like_plan(grid, start, foods, exit_pos, pies, ghosts,
                                     max_expanded=args.max_expanded)
        print(f"Done: cost={met.cost:.0f} | exp={met.expanded} | gen={met.generated} | time={met.time_ms:.1f}ms", flush=True)

        write_files(lay, met)
        print(f"Wrote TXT: {TXT_PATH}")

if __name__ == "__main__":
    main()
    