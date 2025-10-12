import argparse, random, time, csv, os
from astar import astar
from bfs import bfs
from problem import EightPuzzleProblem
from heuristics import HCeilHalf, HPDBAdditive, HMax
from draw_tree import draw_tree
from tree_tracer import SearchTreeTracer
GOALS = [
    ((1,2,3),(4,5,6),(7,8,0)),  # G1
    ((8,7,6),(5,4,3),(2,1,0)),  # G2
    ((0,1,2),(3,4,5),(6,7,8)),  # G3
    ((0,8,7),(6,5,4),(3,2,1)),  # G4
]

def shuffle_state(state, k=5, seed=0):
    random.seed(seed)
    P = EightPuzzleProblem(state, GOALS)
    s = state
    for _ in range(k):
        acts = list(P.actions(s))
        if not acts: break
        s = P.result(s, random.choice(acts))
    return s

class HMax:
    def __init__(self, h1, h2): self.h1, self.h2 = h1, h2
    def h(self, s): return max(self.h1.h(s), self.h2.h(s))

def build_heuristic(name: str, pdb_max_states: int):
    h1 = HCeilHalf(GOALS[0])
    if name == "ceil":
        return h1, "ceil(H/2)"
    if HPDBAdditive is None and name in ("pdb","max"):
        raise RuntimeError("Thiếu heuristics_pdb.py hoặc import lỗi – không dùng được PDB.")
    h2 = HPDBAdditive(GOALS, max_states=pdb_max_states)
    if name == "pdb":
        return h2, f"PDB(additive; max_states={pdb_max_states})"
    if name == "max":
        return HMax(h1, h2), f"max(ceil, PDB[{pdb_max_states}])"
    raise ValueError("heuristic name phải là 'ceil', 'pdb' hoặc 'max'.")

def ensure_dir(path: str):
    d = os.path.dirname(path)
    if d and not os.path.exists(d):
        os.makedirs(d, exist_ok=True)

def append_csv(path: str, rows):
    ensure_dir(path)
    header = ["case_id","seed","shuffle_k","heuristic","algo","cost","expanded","generated","time_ms"]
    write_header = not os.path.exists(path)
    with open(path, "a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if write_header: w.writerow(header)
        for r in rows: w.writerow(r)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--n", type=int, default=1, help="số case random")
    ap.add_argument("--shuffle-k", type=int, default=5, help="số bước xáo trộn state ban đầu")
    ap.add_argument("--heuristic", choices=["ceil","pdb","max"], default="max",
                    help="chọn heuristic: ceil(H/2), PDB additive, hay max(ceil,PDB)")
    ap.add_argument("--pdb-max-states", type=int, default=200_000,
                    help="giới hạn số state duyệt khi dựng mỗi PDB (PartialPDB)")
    ap.add_argument("--draw-n", type=int, default=5, help="số nút đầu tiên trong đường đi để ghi ra file txt")
    # >>> NEW: CSV flags
    ap.add_argument("--export-csv", action="store_true", help="xuất kết quả vào CSV trong thư mục results/")
    ap.add_argument("--csv-path", default="../../results/task1_runs.csv",
                    help="đường dẫn file CSV (mặc định: ../../results/task1_runs.csv)")
    args = ap.parse_args()

    print(f"[CONFIG] heuristic={args.heuristic}, pdb_max_states={args.pdb_max_states}")
    if args.export_csv:
        print(f"[CSV] logging to: {args.csv_path}")

    init = ((1,2,3),(4,5,6),(7,8,0))
    for i in range(args.n):
        s0 = shuffle_state(init, k=args.shuffle_k, seed=args.seed + i)
        prob = EightPuzzleProblem(s0, GOALS)

        # chọn heuristic theo flag
        h, h_name = build_heuristic(args.heuristic, args.pdb_max_states)
        print(f"\n[Case {i}] Heuristic: {h_name}")

        rows = []

        # A*
        tracer = SearchTreeTracer(n_limit=args.draw_n)
        t0 = time.time()
        res_a = astar(prob, h, graph_search=True, on_generate=tracer.on_generate)
        dt_a = (time.time() - t0) * 1000
        # Xuất cây ra DOT để xem trên GraphvizOnline
        os.makedirs("./results", exist_ok=True)
        with open("./results/task1_tree.dot", "w", encoding="utf-8") as f:
            f.write(tracer.to_dot())

        print(f"[A* ] cost={res_a['cost']}, expanded={res_a['expanded']}, generated={res_a['generated']}, time_ms={dt_a:.2f}")
        if args.export_csv:
            rows.append([i, args.seed + i, args.shuffle_k, args.heuristic, "A*", res_a["cost"],
                        res_a["expanded"], res_a["generated"], f"{dt_a:.2f}"])
        # if res_a["solution"]:
        #     draw_tree(res_a["solution"], n=args.draw_n)
        # print(f"[A* ] cost={res_a['cost']}, expanded={res_a['expanded']}, generated={res_a['generated']}, time_ms={dt_a:.2f}")
        # if args.export_csv:
        #     rows.append([i, args.seed + i, args.shuffle_k, args.heuristic, "A*", res_a["cost"], res_a["expanded"], res_a["generated"], f"{dt_a:.2f}"])

        # BFS
        t1 = time.time()
        res_b = bfs(prob, graph_search=True)
        dt_b = (time.time() - t1) * 1000
        print(f"[BFS] cost={res_b['cost']}, expanded={res_b['expanded']}, generated={res_b['generated']}, time_ms={dt_b:.2f}")
        if args.export_csv:
            rows.append([i, args.seed + i, args.shuffle_k, args.heuristic, "BFS", res_b["cost"], res_b["expanded"], res_b["generated"], f"{dt_b:.2f}"])

        if args.export_csv and rows:
            append_csv(args.csv_path, rows)

if __name__ == "__main__":
    main()
