# source/task2_pacman/experiments.py
from __future__ import annotations
import os, sys, argparse, time, glob
import statistics as st

# ----- import nội bộ / đường dẫn -----
BASE_DIR  = os.path.dirname(os.path.abspath(__file__))           # .../source/task2_pacman
TASK2_DIR = BASE_DIR
REPO_ROOT = os.path.abspath(os.path.join(TASK2_DIR, "..", "..")) # gốc repo (có thư mục input/)
if TASK2_DIR not in sys.path:
    sys.path.insert(0, TASK2_DIR)

from astar import astar
from bfs import bfs
from pacman_problem import PacmanProblem

# Heuristic: thử nhiều tên để khớp code của bạn
HeuristicAuto = None

from heuristics import HeuristicPacmanMST as _H
HeuristicAuto = _H

# ======================= I/O & layout =======================
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
            elif ch == 'G': ghosts.append(((r, c), +1))
    if start is None or exit_pos is None:
        raise ValueError("Layout cần có 'P' (start) và 'E' (exit).")
    return start, list(foods), exit_pos, list(pies), ghosts

def resolve_layout_candidates(arg_path: str | None):
    # 1) người dùng truyền file/thư mục/pattern
    if arg_path:
        if os.path.isfile(arg_path):
            return [arg_path]
        if os.path.isdir(arg_path):
            return sorted(glob.glob(os.path.join(arg_path, "*.txt")))
        matches = sorted(glob.glob(arg_path))
        if matches:
            return matches

    # 2) tự tìm file mặc định
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
    raise FileNotFoundError(
        "Không tìm thấy layout. Truyền --layout <file|folder|pattern> hoặc đặt file vào input/task02_pacman_example_map.txt"
    )

# ======================= Heuristic baseline (h=0) =======================
class HeuristicZero:
    def __init__(self, problem=None): self.problem = problem
    def h(self, state): return 0.0

# ======================= Biến thiên nhẹ initial state =======================
def small_randomize(start, foods, exit_pos, pies, ghosts, run_id):
    import random
    random.seed(12345 + run_id)
    ghosts2 = []
    for (pos, d) in ghosts:
        ghosts2.append((pos, d if random.random() < 0.5 else -d))
    rot_idx0 = random.randint(0, 3)
    return start, foods, exit_pos, pies, ghosts2, rot_idx0

# ======================= Xuất ra thư mục output =======================
OUTPUT_DIR = os.path.join(TASK2_DIR, "output")
os.makedirs(OUTPUT_DIR, exist_ok=True)
TXT_REPORT = os.path.join(OUTPUT_DIR, "experiments_report.txt")
CSV_METRICS = os.path.join(OUTPUT_DIR, "experiments_metrics.csv")

def write_txt_report(report_lines: list[str]):
    with open(TXT_REPORT, "w", encoding="utf-8") as f:
        for line in report_lines:
            f.write(line.rstrip() + "\n")

def write_csv_metrics(rows: list[list[str]]):
    header = ["layout", "algo", "runs",
              "cost_avg", "cost_sd",
              "expanded_avg", "generated_avg", "max_frontier_avg", "time_ms_avg"]
    new_file = not os.path.isfile(CSV_METRICS)
    # newline="" tránh dòng trống trên Windows
    with open(CSV_METRICS, "a", encoding="utf-8", newline="") as f:
        if new_file:
            f.write(",".join(header) + "\n")
        for r in rows:
            f.write(",".join(map(str, r)) + "\n")

# ======================= Helper =======================
def _safe_get(res, key, default=0):
    return res.get(key, default) if isinstance(res, dict) else default

def _as_list(xs):
    if xs is None:
        return []
    if isinstance(xs, (list, tuple)):
        return list(xs)
    return [xs]

def avg(xs):
    xs = _as_list(xs)
    return st.mean(xs) if len(xs) else float('nan')

def sd(xs):
    xs = _as_list(xs)
    n = len(xs)
    if n >= 2:
        try:
            return st.pstdev(xs)  # độ lệch chuẩn quần thể
        except Exception:
            return float('nan')
    elif n == 1:
        return 0.0
    else:
        return float('nan')

# ======================= Helper chạy có timeout mềm =======================
def run_with_timeout(fn, timeout_sec: float):
    """
    Chạy fn() và trả (res, elapsed_ms, hit_timeout: bool).
    Timeout mềm: chỉ đánh dấu nếu quá thời gian; không cưỡng bức ngắt fn().
    Hiệu quả cắt sớm tốt nhất là dùng --max-expanded cho A*.
    """
    t0 = time.time()
    res = fn()
    dt = (time.time() - t0) * 1000.0
    hit = (timeout_sec > 0 and dt > timeout_sec * 1000.0)
    return res, dt, hit

# ======================= main =======================
def main():
    if HeuristicAuto is None:
        raise ImportError("Không tìm được lớp heuristic phù hợp. Kiểm tra heuristics.py (nên có HeuristicTeleportAware / HeuristicPacmanMSTDynamicTeleport).")

    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default="", help="File | folder | glob pattern của layout (.txt).")
    ap.add_argument("--runs", type=int, default=5, help="Số lần lặp mỗi layout (randomize state nhẹ).")
    ap.add_argument("--fast", action="store_true", help="Chế độ nhanh: runs=1, skip BFS, max_expanded=200000")
    ap.add_argument("--no-bfs", action="store_true", help="Bỏ BFS (chỉ chạy A* với 2 heuristic).")
    ap.add_argument("--max-expanded", type=int, default=0, help="Giới hạn số node expand cho A*. 0 = không giới hạn.")
    ap.add_argument("--timeout-sec", type=float, default=0.0, help="Timeout mềm mỗi lần chạy (giây). 0 = không giới hạn.")
    args = ap.parse_args()

    # áp dụng chế độ nhanh
    if args.fast:
        args.runs = 1
        args.no_bfs = True
        if args.max_expanded == 0:
            args.max_expanded = 200000

    layouts = resolve_layout_candidates(args.layout)

    # 3 cấu hình: A*(h=0), A*(h=TeleportAware/MST), BFS
    algos = [
        ("A*-h0", "astar_h0"),
        ("A*-TeleportAware", "astar_mst_tele"),
        ("BFS", "bfs"),
    ]

    report_lines = []
    csv_rows = []

    for lay_path in layouts:
        grid = load_layout_file(lay_path)
        start, foods, exit_pos, pies, ghosts = parse_layout(grid)

        stats = {name: {"cost": [], "expanded": [], "generated": [], "max_frontier": [], "time_ms": []}
                 for name, _ in algos}

        for run_id in range(args.runs):
            s0, f0, e0, p0, g0, rot0 = small_randomize(start, list(foods), exit_pos, list(pies), list(ghosts), run_id)

            def make_prob():
                # TTL=0; steps_mod30_0=0; rot_idx0 = rot0
                return PacmanProblem(
                    grid, s0, f0, e0,
                    pies=p0, ghosts=g0,
                    ttl0=0, steps_mod30_0=0, rot_idx0=rot0
                )

            # --- A*(h=0)
            prob = make_prob()
            h0 = HeuristicZero(prob)
            def _run_astar_h0():
                if args.max_expanded and args.max_expanded > 0:
                    try:
                        return astar(prob, h0, graph_search=True, max_expanded=args.max_expanded)
                    except TypeError:
                        pass
                return astar(prob, h0, graph_search=True)
            res, t_ms, _ = run_with_timeout(_run_astar_h0, args.timeout_sec)
            stats["A*-h0"]["cost"].append(_safe_get(res, "cost", 0))
            stats["A*-h0"]["expanded"].append(_safe_get(res, "expanded", 0))
            stats["A*-h0"]["generated"].append(_safe_get(res, "generated", 0))
            stats["A*-h0"]["max_frontier"].append(_safe_get(res, "max_frontier", 0))
            stats["A*-h0"]["time_ms"].append(t_ms)

            # --- A*(h=TeleportAware/MST)
            prob = make_prob()
            hz = HeuristicAuto(prob)
            def _run_astar_mst():
                if args.max_expanded and args.max_expanded > 0:
                    try:
                        return astar(prob, hz, graph_search=True, max_expanded=args.max_expanded)
                    except TypeError:
                        pass
                return astar(prob, hz, graph_search=True)
            res, t_ms, _ = run_with_timeout(_run_astar_mst, args.timeout_sec)
            stats["A*-TeleportAware"]["cost"].append(_safe_get(res, "cost", 0))
            stats["A*-TeleportAware"]["expanded"].append(_safe_get(res, "expanded", 0))
            stats["A*-TeleportAware"]["generated"].append(_safe_get(res, "generated", 0))
            stats["A*-TeleportAware"]["max_frontier"].append(_safe_get(res, "max_frontier", 0))
            stats["A*-TeleportAware"]["time_ms"].append(t_ms)

            # --- BFS (có thể rất chậm; cho phép tắt bằng --no-bfs)
            if not args.no_bfs:
                prob = make_prob()
                def _run_bfs():
                    return bfs(prob, graph_search=True)
                res, t_ms, _ = run_with_timeout(_run_bfs, args.timeout_sec)
                stats["BFS"]["cost"].append(_safe_get(res, "cost", 0))
                stats["BFS"]["expanded"].append(_safe_get(res, "expanded", 0))
                stats["BFS"]["generated"].append(_safe_get(res, "generated", 0))
                stats["BFS"]["max_frontier"].append(_safe_get(res, "max_frontier", 0))
                stats["BFS"]["time_ms"].append(t_ms)

        # ----- Tóm tắt cho layout này -----
        report_lines.append(f"=== LAYOUT: {lay_path} ===")
        for name, _ in algos:
            if name == "BFS" and args.no_bfs:
                continue
            cost_avg = avg(stats[name]["cost"]); cost_sd = sd(stats[name]["cost"])
            exp_avg  = avg(stats[name]["expanded"])
            gen_avg  = avg(stats[name]["generated"])
            mf_avg   = avg(stats[name]["max_frontier"])
            t_avg    = avg(stats[name]["time_ms"])
            report_lines.append(
                f"[{name}] runs={args.runs} | "
                f"cost={cost_avg:.2f}±{cost_sd:.2f}, "
                f"expanded={exp_avg:.2f}, generated={gen_avg:.2f}, "
                f"max_frontier={mf_avg:.2f}, time_ms={t_avg:.2f}"
            )
            csv_rows.append([
                lay_path, name, args.runs,
                f"{cost_avg:.2f}", f"{cost_sd:.2f}",
                f"{exp_avg:.2f}", f"{gen_avg:.2f}", f"{mf_avg:.2f}", f"{t_avg:.2f}"
            ])

    # Ghi kết quả vào thư mục output
    write_txt_report(report_lines)
    write_csv_metrics(csv_rows)
    print(f"\nĐã ghi: {TXT_REPORT}")
    print(f"Đã ghi: {CSV_METRICS}")
    print("Gợi ý chạy nhanh: --fast (runs=1, no-bfs, max_expanded=200000)")

if __name__ == "__main__":
    main()
