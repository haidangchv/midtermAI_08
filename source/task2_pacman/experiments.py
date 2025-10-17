from __future__ import annotations
import sys
import argparse, os, time, csv
from astar import astar
from bfs import bfs
from pacman_problem import PacmanProblem
from heuristics import HeuristicPacmanMST

# ----- IMPORT PATHS -----
BASE_DIR = os.path.dirname(os.path.abspath(__file__))           # .../source/task2_pacman/gui
TASK2_DIR = os.path.abspath(os.path.join(BASE_DIR, ".."))       # .../source/task2_pacman
sys.path.insert(0, TASK2_DIR)
# Dùng file bạn đã upload làm layout mặc định (đường dẫn tương đối từ file này)
DEFAULT_LAYOUT = os.path.abspath(os.path.join(TASK2_DIR,  "..", "task02_pacman_example_map.txt"))
    

def load_layout(layout_arg: str):
    if not os.path.exists(layout_arg):
        raise FileNotFoundError(f"Layout file không tồn tại: {layout_arg}")
    with open(layout_arg, "r", encoding="utf-8") as f:
        lines = [line.rstrip("\n") for line in f if line.strip("\n")]
    if not lines:
        raise ValueError("Layout file rỗng.")
    w = max(len(x) for x in lines)
    return [row.ljust(w) for row in lines]

def parse_layout(grid):
    start = None; foods = []; exit_pos = None; pies = []; ghosts = []
    for r,row in enumerate(grid):
        for c,ch in enumerate(row):
            if ch == 'P': start = (r,c)
            elif ch == '.': foods.append((r,c))
            elif ch == 'E': exit_pos = (r,c)
            elif ch == 'O': pies.append((r,c))
            elif ch == 'G': ghosts.append(((r,c), +1))
    if start is None or exit_pos is None:
        raise ValueError("Layout phải có cả 'P' (start) và 'E' (exit).")
    return start, foods, exit_pos, pies, ghosts

# CSV helpers
def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def append_csv(path: str, rows):
    ensure_dir(path)
    header = ["layout","algo","cost","expanded","generated","max_frontier","time_ms"]
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header: w.writerow(header)
        for r in rows: w.writerow(r)

def extract_actions_from_astar(result):
    if not result.get("solution"): return []
    return [n.action for n in result["solution"][1:]]

def extract_actions_from_bfs(result):
    if not result.get("solution"): return []
    return [n["action"] for n in result["solution"][1:]]

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--layout", default=DEFAULT_LAYOUT,
                    help="Đường dẫn file layout (.txt).")
    ap.add_argument("--export-csv", action="store_true",
                    help="Xuất kết quả vào CSV trong thư mục results/")
    ap.add_argument("--csv-path", default="../../results/task2_runs.csv",
                    help="Đường dẫn file CSV (mặc định: ../../results/task2_runs.csv)")
    args = ap.parse_args()

    grid = load_layout(args.layout)
    start, foods, exit_pos, pies, ghosts = parse_layout(grid)

    prob = PacmanProblem(grid, start, foods, exit_pos, pies=pies, ghosts=ghosts)
    h = HeuristicPacmanMST(grid, exit_pos)

    rows = []

    # A*
    t0 = time.time()
    res_a = astar(prob, h, graph_search=True)
    dt_a = (time.time() - t0) * 1000.0
    print(f"[A* ] cost={res_a['cost']}, expanded={res_a['expanded']}, generated={res_a['generated']}, max_frontier={res_a.get('max_frontier')}, time_ms={dt_a:.2f}")
    a_actions = extract_actions_from_astar(res_a)
    print(f"[A* ] actions: {''.join(a_actions)}")
    rows.append([args.layout, "A*", res_a["cost"], res_a["expanded"], res_a["generated"], res_a.get("max_frontier"), f"{dt_a:.2f}"])

    # BFS
    t1 = time.time()
    res_b = bfs(prob, graph_search=True)
    dt_b = (time.time() - t1) * 1000.0
    print(f"[BFS] cost={res_b['cost']}, expanded={res_b['expanded']}, generated={res_b['generated']}, max_frontier={res_b.get('max_frontier')}, time_ms={dt_b:.2f}")
    b_actions = extract_actions_from_bfs(res_b)
    print(f"[BFS] actions: {''.join(b_actions)}")
    rows.append([args.layout, "BFS", res_b["cost"], res_b["expanded"], res_b["generated"], res_b.get("max_frontier"), f"{dt_b:.2f}"])

    if args.export_csv:
        append_csv(args.csv_path, rows)

if __name__ == "__main__":
    main()
