from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, Iterable, List, Optional, Tuple, Set
import heapq
import random
import time
import os, shutil
from collections import deque

# ----------------------------
# Kiểu trạng thái: Tuple[Tuple[int, ...], ...] kích thước 3x3; 0 là ô trống
Grid = Tuple[Tuple[int, int, int], Tuple[int, int, int], Tuple[int, int, int]]

# ------------------------------------------------
# Hỗ trợ Graphviz 'dot'
def _inject_dot_into_env(dot_path: Optional[str]) -> None:
    """
    Thêm dot.exe vào PATH và đặt GRAPHVIZ_DOT nếu dot_path được cung cấp.
    Nếu dot_path là thư mục, tự nối 'dot.exe'.
    """
    if not dot_path:
        return
    if os.path.isdir(dot_path):
        dot_path = os.path.join(dot_path, "dot.exe")
    if os.path.isfile(dot_path):
        dot_dir = os.path.dirname(dot_path)
        os.environ["PATH"] = f"{dot_dir};" + os.environ.get("PATH", "")
        os.environ["GRAPHVIZ_DOT"] = dot_path

def _ensure_dot_available(extra_candidates: Optional[List[str]] = None) -> Optional[str]:
    """
    Tìm dot.exe trong PATH; nếu không có, thử thêm các vị trí phổ biến.
    Trả về đường dẫn dot (hoặc None nếu vẫn không tìm thấy).
    """
    cur = shutil.which("dot")
    if cur:
        return cur
    candidates = [
        r"C:\Program Files\Graphviz\bin\dot.exe",
        r"C:\Program Files (x86)\Graphviz2.38\bin\dot.exe",
        os.path.join(os.environ.get("CONDA_PREFIX", ""), r"Library\bin\dot.exe"),
    ]
    if extra_candidates:
        candidates = extra_candidates + candidates
    for p in candidates:
        if p and os.path.isfile(p):
            _inject_dot_into_env(p)
            return p
    return None

# ------------------------------------------------
# Utilities
def find_pos(g: Grid, val: int) -> Tuple[int, int]:
    for i in range(3):
        for j in range(3):
            if g[i][j] == val:
                return (i, j)
    raise ValueError("Value not found")

def swap_cells(g: Grid, p1: Tuple[int, int], p2: Tuple[int, int]) -> Grid:
    (i1, j1), (i2, j2) = p1, p2
    lst = [list(row) for row in g]
    lst[i1][j1], lst[i2][j2] = lst[i2][j2], lst[i1][j1]
    return tuple(tuple(row) for row in lst)  # type: ignore

def move_blank(g: Grid, direction: str) -> Optional[Grid]:
    """Di chuyển ô trống theo U/D/L/R nếu có thể."""
    di = {"U": -1, "D": 1, "L": 0, "R": 0}
    dj = {"U": 0, "D": 0, "L": -1, "R": 1}
    bi, bj = find_pos(g, 0)
    ni, nj = bi + di[direction], bj + dj[direction]
    if 0 <= ni < 3 and 0 <= nj < 3:
        return swap_cells(g, (bi, bj), (ni, nj))
    return None

# ------------------------------------------------
# Action
@dataclass(frozen=True)
class Action:
    kind: str  # "move" | "swap9" | "swap_corners"
    detail: str
    def __str__(self) -> str:
        return f"{self.kind}:{self.detail}"

# ------------------------------------------------
# Problem tổng quát
class Problem:
    def __init__(self, initial: Any):
        self.initial = initial

    def is_goal(self, state: Any) -> bool: ...
    def actions(self, state: Any) -> Iterable[Action]: ...
    def result(self, state: Any, action: Action) -> Any: ...
    def step_cost(self, state: Any, action: Action, next_state: Any) -> float:
        return 1.0  # cost = 1 cho mỗi action theo đề

# ------------------------------------------------
# 8-PUZZLE theo luật đề, VỚI 4 GOALS CỐ ĐỊNH như đề/mã cũ
class EightPuzzleProblem(Problem):
    def __init__(self, initial: Grid, goals: Optional[List[Grid]] = None):
        super().__init__(initial)
        if goals is None:
            fixed_goals: List[Grid] = [
                ((1, 2, 3), (4, 5, 6), (7, 8, 0)),
                ((8, 7, 6), (5, 4, 3), (2, 1, 0)),
                ((0, 1, 2), (3, 4, 5), (6, 7, 8)),
                ((0, 8, 7), (6, 5, 4), (3, 2, 1)),
            ]
            self.goals = fixed_goals
        else:
            self.goals = goals

    def is_goal(self, state: Grid) -> bool:
        return state in self.goals

    def actions(self, state: Grid) -> Iterable[Action]:
        # (1) Blank moves
        for d in ("U", "D", "L", "R"):
            nxt = move_blank(state, d)
            if nxt is not None:
                yield Action("move", d)

        # (2) Swap cặp kề nhau có tổng = 9 (không chứa ô trống)
        dirs = [(1,0), (-1,0), (0,1), (0,-1)]
        for i in range(3):
            for j in range(3):
                a = state[i][j]
                if a == 0:
                    continue
                for di, dj in dirs:
                    ni, nj = i + di, j + dj
                    if 0 <= ni < 3 and 0 <= nj < 3:
                        b = state[ni][nj]
                        # (i,j) < (ni,nj) để không sinh trùng cặp
                        if b != 0 and a + b == 9 and (i, j) < (ni, nj):
                            yield Action("swap9", f"({i},{j})<->({ni},{nj})")

        # (3) Swap corners TL↔BR, TR↔BL (ô trống không được swap)
        corners = {
            "TL_BR": ((0,0), (2,2)),
            "TR_BL": ((0,2), (2,0)),
        }
        for name, (p1, p2) in corners.items():
            (i1,j1), (i2,j2) = p1, p2
            if state[i1][j1] != 0 and state[i2][j2] != 0:
                yield Action("swap_corners", name)

    def result(self, state: Grid, action: Action) -> Grid:
        if action.kind == "move":
            nxt = move_blank(state, action.detail)
            assert nxt is not None
            return nxt
        elif action.kind == "swap9":
            lhs, rhs = action.detail.split("<->")
            i, j = map(int, lhs.strip()[1:-1].split(","))
            ni, nj = map(int, rhs.strip()[1:-1].split(","))
            return swap_cells(state, (i,j), (ni,nj))
        elif action.kind == "swap_corners":
            if action.detail == "TL_BR":
                return swap_cells(state, (0,0), (2,2))
            else:
                return swap_cells(state, (0,2), (2,0))
        else:
            raise ValueError("Unknown action")

# ------------------------------------------------
# Node
@dataclass(order=True)
class Node:
    f: float
    id: int = field(compare=False)
    state: Any = field(compare=False)
    g: float = field(compare=False, default=0.0)
    parent: Optional["Node"] = field(compare=False, default=None)
    action: Optional[Action] = field(compare=False, default=None)

    def path(self) -> List["Node"]:
        cur: Optional[Node] = self
        out: List[Node] = []
        while cur is not None:
            out.append(cur)
            cur = cur.parent
        return out[::-1]

# ------------------------------------------------
# Heuristics (admissible + consistent cho luật swap)
def misplaced_tiles_min_over_goals(state: Grid, goals: List[Grid]) -> int:
    best = 9
    for g in goals:
        cnt = 0
        for i in range(3):
            for j in range(3):
                if state[i][j] != 0 and state[i][j] != g[i][j]:
                    cnt += 1
        best = min(best, cnt)
    return best

def h_zero(state: Grid, problem: EightPuzzleProblem) -> float:
    return 0.0

def h_pair(state: Grid, problem: EightPuzzleProblem) -> float:
    # Số ô sai vị trí (tối ưu theo 4 goal), mỗi bước có thể sửa tối đa 2 ô => ceil(mis/2)
    mis = misplaced_tiles_min_over_goals(state, problem.goals)
    return float((mis + 1) // 2)

# ------------------------------------------------
# A* tổng quát
class AStar:
    def __init__(self,
                 problem: Problem,
                 heuristic: Callable[[Any, Problem], float]):
        self.problem = problem
        self.heuristic = heuristic
        self._next_id = 0
        self.expanded_nodes = 0
        self.trace_edges: List[Tuple[int, int, str]] = []  # (parent_id, child_id, action)
        self._id2state: Dict[int, Any] = {}

    def _new_id(self) -> int:
        self._next_id += 1
        return self._next_id

    def solve(self, max_expansions: Optional[int] = None) -> Optional[Node]:
        start = Node(f=0.0, id=self._new_id(), state=self.problem.initial, g=0.0, parent=None, action=None)
        self._id2state[start.id] = start.state
        start.f = start.g + self.heuristic(start.state, self.problem)

        frontier: List[Node] = []
        heapq.heappush(frontier, start)

        g_best: Dict[Any, float] = {start.state: 0.0}
        closed: Set[Any] = set()

        while frontier:
            cur = heapq.heappop(frontier)
            if self.problem.is_goal(cur.state):
                return cur
            if cur.state in closed:
                continue
            closed.add(cur.state)

            self.expanded_nodes += 1
            if max_expansions is not None and self.expanded_nodes >= max_expansions:
                return None

            for act in self.problem.actions(cur.state):
                nxt_state = self.problem.result(cur.state, act)
                new_g = cur.g + self.problem.step_cost(cur.state, act, nxt_state)
                if nxt_state in g_best and new_g >= g_best[nxt_state]:
                    continue
                g_best[nxt_state] = new_g
                child = Node(f=0.0, id=self._new_id(), state=nxt_state, g=new_g, parent=cur, action=act)
                child.f = child.g + self.heuristic(child.state, self.problem)
                self._id2state[child.id] = child.state
                heapq.heappush(frontier, child)
                self.trace_edges.append((cur.id, child.id, str(act)))
        return None

    def export_search_tree_dot(self, limit_edges: int = 100) -> str:
        lines = ["digraph G {", '  node [shape=box, fontsize=10];']
        used_nodes: Set[int] = set()
        def state_label(state: Grid) -> str:
            flat = sum(state, ())
            return "\\n".join([
                f"{flat[0]} {flat[1]} {flat[2]}",
                f"{flat[3]} {flat[4]} {flat[5]}",
                f"{flat[6]} {flat[7]} {flat[8]}",
            ])
        for (p, c, a) in self.trace_edges[:limit_edges]:
            used_nodes.add(p); used_nodes.add(c)
            lines.append(f'  {p} -> {c} [label="{a}", fontsize=9];')
        for nid in used_nodes:
            st = self._id2state.get(nid)
            if st is not None:
                lbl = state_label(st)
                lines.append(f'  {nid} [label="{lbl}"];')
        lines.append("}")
        return "\n".join(lines)

# ------------------------------------------------
# BFS (để so sánh time/space/cost)
class BFS:
    def __init__(self, problem: Problem):
        self.problem = problem
        self.expanded_nodes = 0

    def solve(self, max_expansions: Optional[int] = None) -> Optional[Node]:
        start = Node(f=0.0, id=0, state=self.problem.initial, g=0.0, parent=None, action=None)
        q = deque([start])
        visited: Set[Any] = {start.state}
        while q:
            cur = q.popleft()
            if self.problem.is_goal(cur.state):
                return cur
            self.expanded_nodes += 1
            if max_expansions is not None and self.expanded_nodes >= max_expansions:
                return None
            for act in self.problem.actions(cur.state):
                nxt = self.problem.result(cur.state, act)
                if nxt not in visited:
                    visited.add(nxt)
                    child = Node(f=0.0, id=0, state=nxt, g=cur.g + 1, parent=cur, action=act)
                    q.append(child)
        return None

# ------------------------------------------------
# Sinh trạng thái ngẫu nhiên solvable (từ 1 goal bằng cách áp dụng action hợp lệ)
def random_state_from_goal(problem: EightPuzzleProblem, steps: int = 50, seed: Optional[int] = None) -> Grid:
    rnd = random.Random(seed)
    goal = rnd.choice(problem.goals)
    s: Grid = goal
    for _ in range(steps):
        acts = list(problem.actions(s))
        if not acts:
            break
        a = rnd.choice(acts)
        s = problem.result(s, a)
    return s

# ------------------------------------------------
# Thí nghiệm
@dataclass
class RunStats:
    found: bool
    path_cost: Optional[int]
    expanded: int
    elapsed_sec: float

def run_once_with_solver(solver_factory: Callable[[], Any]) -> RunStats:
    t0 = time.perf_counter()
    solver = solver_factory()
    if isinstance(solver, AStar):
        goal = solver.solve()
        elapsed = time.perf_counter() - t0
        if goal is None:
            return RunStats(False, None, solver.expanded_nodes, elapsed)
        return RunStats(True, int(goal.g), solver.expanded_nodes, elapsed)
    elif isinstance(solver, BFS):
        goal = solver.solve()
        elapsed = time.perf_counter() - t0
        if goal is None:
            return RunStats(False, None, solver.expanded_nodes, elapsed)
        return RunStats(True, int(goal.g), solver.expanded_nodes, elapsed)
    else:
        raise ValueError("Unknown solver")

def experiment_compare(initial_states: List[Grid],
                       goals: Optional[List[Grid]] = None) -> Dict[str, List[RunStats]]:
    results: Dict[str, List[RunStats]] = {"A*_h0": [], "A*_hpair": [], "BFS": []}
    for s in initial_states:
        prob = EightPuzzleProblem(s, goals=goals)
        # A* with h0
        results["A*_h0"].append(
            run_once_with_solver(lambda p=prob: AStar(p, h_zero))
        )
        # A* with h_pair
        results["A*_hpair"].append(
            run_once_with_solver(lambda p=prob: AStar(p, h_pair))
        )
        # BFS
        results["BFS"].append(
            run_once_with_solver(lambda p=prob: BFS(p))
        )
    return results

def summarize_results(results: Dict[str, List[RunStats]]) -> Dict[str, Dict[str, float]]:
    summary: Dict[str, Dict[str, float]] = {}
    for name, stats in results.items():
        founds = [s for s in stats if s.found]
        summary[name] = {
            "trials": float(len(stats)),
            "found_rate": float(len(founds)) / max(1, len(stats)),
            "avg_cost": (sum(s.path_cost for s in founds if s.path_cost is not None) / max(1, len(founds))) if founds else float("nan"),
            "avg_expanded": sum(s.expanded for s in stats) / max(1, len(stats)),
            "avg_time_ms": 1000.0 * (sum(s.elapsed_sec for s in stats) / max(1, len(stats))),
        }
    return summary

def print_table_from_summary(title: str, summary: Dict[str, Dict[str, float]]) -> None:
    print(f"\nBẢNG 4 — {title}")
    print("=" * 90)
    print(f"{'Thuật toán':<26}{'Trials':>8}{'Found%':>10}{'Avg Cost':>12}{'Avg Expanded':>15}{'Avg Time (ms)':>15}")
    print("-" * 90)
    order = ["A*_h0", "A*_hpair", "BFS"]
    for k in order:
        if k in summary:
            row = summary[k]
            print(f"{k:<26}{row['trials']:>8.0f}{row['found_rate']*100:>9.1f}%{row['avg_cost']:>12.2f}{row['avg_expanded']:>15.2f}{row['avg_time_ms']:>15.2f}")
    for k, row in summary.items():
        if k not in order:
            print(f"{k:<26}{row['trials']:>8.0f}{row['found_rate']*100:>9.1f}%{row['avg_cost']:>12.2f}{row['avg_expanded']:>15.2f}{row['avg_time_ms']:>15.2f}")
    print("=" * 90)

# ------------------------------------------------
# Trình bày trạng thái/đường đi
def print_grid(g: Grid) -> None:
    for i in range(3):
        print(" ".join(str(x) for x in g[i]))
    print()

def print_solution(node: Optional[Node]) -> None:
    if node is None:
        print("No solution.")
        return
    path = node.path()
    print(f"Path length (cost): {int(path[-1].g)}  |  steps = {len(path)-1}")
    for k, nd in enumerate(path):
        print(f"Step {k}:")
        print_grid(nd.state)
        if nd.action:
            print(f"Action: {nd.action}")
            print("-"*20)

# ------------------------------------------------
# ======= ĐÁNH GIÁ H: h*(n) bằng BFS, admissibility & consistency =======

def bfs_optimal_cost_from_state(problem: Problem, start_state: Grid) -> int:
    """Trả về h*(n): số bước tối ưu từ start_state đến 1 trong các goal (BFS, cost=1/step)."""
    q = deque([(start_state, 0)])
    seen = {start_state}
    while q:
        s, d = q.popleft()
        if problem.is_goal(s):
            return d
        for act in problem.actions(s):
            ns = problem.result(s, act)
            if ns not in seen:
                seen.add(ns)
                q.append((ns, d + 1))
    return float("inf")

def evaluate_admissibility_along_path(problem: EightPuzzleProblem,
                                      heuristic: Callable[[Grid, EightPuzzleProblem], float],
                                      solution_node: Node) -> List[dict]:
    """
    BẢNG — ADMISSIBLE (h(n) ≤ h*(n)) DỌC THEO ĐƯỜNG ĐI NGHIỆM
    """
    rows: List[dict] = []
    path = solution_node.path()
    print("\nBẢNG — ADMISSIBLE (h(n) ≤ h*(n)) DỌC THEO ĐƯỜNG ĐI NGHIỆM")
    print("=" * 80)
    print(f"{'Bước':<8}{'h(n)':<12}{'h*(n) = cost tối ưu':<24}{'Kết luận'}")
    print("-" * 80)
    for k, nd in enumerate(path):
        h_n = heuristic(nd.state, problem)
        h_star = bfs_optimal_cost_from_state(problem, nd.state)
        ok = h_n <= h_star
        rows.append({"step": k, "h": h_n, "h_star": h_star, "ok": ok})
        print(f"{k:<8}{int(h_n):<12}{h_star:<24}{'Đúng' if ok else 'Sai'}")
    print("=" * 80)
    return rows

def evaluate_consistency_for_state(problem: EightPuzzleProblem,
                                   heuristic: Callable[[Grid, EightPuzzleProblem], float],
                                   state: Grid) -> List[dict]:
    """
    BẢNG — CONSISTENT TẠI 1 TRẠNG THÁI (h(n) ≤ 1 + h(n'))
    """
    rows: List[dict] = []
    h_n = heuristic(state, problem)
    print("\nBẢNG — CONSISTENT TẠI 1 TRẠNG THÁI (h(n) ≤ 1 + h(n'))")
    print("=" * 110)
    # Dùng .format để tránh backslash trong f-string
    print("{:<10}{:<10}{:<12}{:<14}{:<12}{}".format(
        "Kế thừa", "h(n)", "h(n')", "1 + h(n')", "Kết luận", "Hành động"
    ))
    print("-" * 110)
    idx = 0
    for act in problem.actions(state):
        nstate = problem.result(state, act)
        h_np = heuristic(nstate, problem)
        consistent = h_n <= 1 + h_np
        idx += 1
        rows.append({"k": idx, "action": str(act), "h_n": h_n, "h_np": h_np, "ok": consistent})
        print("{:<10}{:<10}{:<12}{:<14}{:<12}{}".format(
            idx, int(h_n), int(h_np), int(1 + h_np), "Đúng" if consistent else "Sai", act
        ))
    print("=" * 110)
    return rows

def evaluate_consistency_along_path(problem: EightPuzzleProblem,
                                    heuristic: Callable[[Grid, EightPuzzleProblem], float],
                                    solution_node: Node,
                                    max_steps: int = 10) -> List[List[dict]]:
    """
    BẢNG — CONSISTENT TRÊN K BƯỚC ĐẦU CỦA ĐƯỜNG ĐI NGHIỆM
    Với mỗi bước k (tối đa max_steps), kiểm tra h(n) ≤ 1 + h(n') cho mọi successor.
    """
    all_rows: List[List[dict]] = []
    path = solution_node.path()
    upto = min(len(path), max_steps)
    print(f"\nBẢNG — CONSISTENT TRÊN {upto} BƯỚC ĐẦU CỦA ĐƯỜNG ĐI NGHIỆM")
    for k in range(upto):
        print(f"\n--- Trạng thái tại bước {k} ---")
        rows = evaluate_consistency_for_state(problem, heuristic, path[k].state)
        all_rows.append(rows)
    return all_rows

# ------------------------------------------------
# ======= Render PNG bằng Graphviz + biến thể “đúng n NÚT” =======

def render_search_tree_png(astar: AStar, max_edges: int = 100, filename: str = "search_tree",
                           dot_path: Optional[str] = None):
    """
    Vẽ cây theo GIỚI HẠN SỐ CẠNH (max_edges). Nếu thiếu 'dot', tự xuất .dot để render thủ công.
    """
    try:
        from graphviz import Digraph
    except Exception as e:
        dot_src = astar.export_search_tree_dot(limit_edges=max_edges)
        with open(f"{filename}.dot", "w", encoding="utf-8") as f:
            f.write(dot_src)
        print(f"Graphviz (Python) chưa sẵn sàng ({e}). Đã ghi DOT vào {filename}.dot")
        print(f">> Render thủ công: dot -Tpng {filename}.dot -o {filename}.png")
        return

    # Tiêm dot_path (nếu có) hoặc tự tìm
    if dot_path:
        _inject_dot_into_env(dot_path)
    else:
        _ensure_dot_available()

    print("dot being used:", shutil.which("dot"))  # giúp kiểm tra nhanh

    dot = Digraph(format="png")
    used_nodes: set[int] = set()

    for (p, c, a) in astar.trace_edges[:max_edges]:
        used_nodes.add(p); used_nodes.add(c)
        dot.edge(str(p), str(c), label=a)

    def label_for_state(state: Grid) -> str:
        return "\n".join(" ".join("_" if v == 0 else str(v) for v in row) for row in state)

    for nid in used_nodes:
        st = astar._id2state.get(nid)
        if st is not None:
            dot.node(str(nid), label_for_state(st))

    try:
        path = dot.render(filename=filename, cleanup=True)
        print(f"Search tree rendered to: {path}")
    except Exception as e:
        dot_src = astar.export_search_tree_dot(limit_edges=max_edges)
        with open(f"{filename}.dot", "w", encoding="utf-8") as f:
            f.write(dot_src)
        print(f"Không chạy được dot ({e}). Đã ghi DOT vào {filename}.dot")
        print(f">> Render thủ công: dot -Tpng {filename}.dot -o {filename}.png")

def export_dot_by_nodes(astar: AStar, max_nodes: int = 30) -> str:
    """
    Xuất DOT với đúng 'max_nodes' NÚT đầu tiên theo thứ tự xuất hiện (root trước, rồi theo trace_edges).
    """
    lines = ["digraph G {", '  node [shape=box, fontsize=10];']

    # Chọn thứ tự nút: gốc trước, rồi theo trace_edges
    ordered_nodes: List[int] = []
    seen: Set[int] = set()
    root_id = min(astar._id2state.keys()) if astar._id2state else None
    if root_id is not None:
        ordered_nodes.append(root_id); seen.add(root_id)
    for (p, c, _a) in astar.trace_edges:
        if p not in seen:
            ordered_nodes.append(p); seen.add(p)
        if c not in seen:
            ordered_nodes.append(c); seen.add(c)
        if len(ordered_nodes) >= max_nodes:
            break
    selected = set(ordered_nodes[:max_nodes])

    # Edges chỉ giữa các nút đã chọn
    for (p, c, a) in astar.trace_edges:
        if p in selected and c in selected:
            lines.append(f'  {p} -> {c} [label="{a}", fontsize=9];')

    # Node labels
    def state_label(state: Grid) -> str:
        flat = sum(state, ())
        return "\\n".join([
            f"{flat[0]} {flat[1]} {flat[2]}",
            f"{flat[3]} {flat[4]} {flat[5]}",
            f"{flat[6]} {flat[7]} {flat[8]}",
        ])
    for nid in ordered_nodes[:max_nodes]:
        st = astar._id2state.get(nid)
        if st is not None:
            lbl = state_label(st)
            lines.append(f'  {nid} [label="{lbl}"];')
    lines.append("}")
    return "\n".join(lines)

def render_search_tree_png_by_nodes(astar: AStar, max_nodes: int = 30, filename: str = "search_tree_n",
                                    dot_path: Optional[str] = None):
    """
    Vẽ cây với ĐÚNG 'max_nodes' NÚT đầu tiên. Nếu thiếu 'dot', xuất .dot để render thủ công.
    """
    try:
        from graphviz import Digraph
    except Exception as e:
        dot_src = export_dot_by_nodes(astar, max_nodes)
        with open(f"{filename}.dot", "w", encoding="utf-8") as f:
            f.write(dot_src)
        print(f"Graphviz (Python) chưa sẵn sàng ({e}). Đã ghi DOT vào {filename}.dot")
        print(f">> Render thủ công: dot -Tpng {filename}.dot -o {filename}.png")
        return

    if dot_path:
        _inject_dot_into_env(dot_path)
    else:
        _ensure_dot_available()

    print("dot being used:", shutil.which("dot"))

    # Chọn đúng max_nodes
    ordered_nodes: List[int] = []
    seen: Set[int] = set()
    root_id = min(astar._id2state.keys()) if astar._id2state else None
    if root_id is not None:
        ordered_nodes.append(root_id); seen.add(root_id)
    for (p, c, _a) in astar.trace_edges:
        if p not in seen:
            ordered_nodes.append(p); seen.add(p)
        if c not in seen:
            ordered_nodes.append(c); seen.add(c)
        if len(ordered_nodes) >= max_nodes:
            break
    selected = set(ordered_nodes[:max_nodes])

    dot = Digraph(format="png")

    def label_for_state(state: Grid) -> str:
        return "\n".join(" ".join("_" if v == 0 else str(v) for v in row) for row in state)

    for nid in ordered_nodes[:max_nodes]:
        st = astar._id2state.get(nid)
        if st is not None:
            dot.node(str(nid), label_for_state(st))

    for (p, c, a) in astar.trace_edges:
        if p in selected and c in selected:
            dot.edge(str(p), str(c), label=a)

    try:
        path = dot.render(filename=filename, cleanup=True)
        print(f"Search tree rendered to: {path}")
    except Exception as e:
        dot_src = export_dot_by_nodes(astar, max_nodes)
        with open(f"{filename}.dot", "w", encoding="utf-8") as f:
            f.write(dot_src)
        print(f"Không chạy được dot ({e}). Đã ghi DOT vào {filename}.dot")
        print(f">> Render thủ công: dot -Tpng {filename}.dot -o {filename}.png")

# ------------------------------------------------
# Ví dụ chạy nhanh + đánh giá heuristic + thí nghiệm
if __name__ == "__main__":
    # 1) Tạo bài toán từ một trạng thái ban đầu
    initial: Grid = ((2, 8, 3),
                     (1, 6, 4),
                     (7, 0, 5))

    problem = EightPuzzleProblem(initial)

    # 2) Giải bằng A* với h_pair (admissible + consistent)
    print("=== A* with h_pair ===")
    astar = AStar(problem, h_pair)
    goal = astar.solve()
    print_solution(goal)
    print(f"Expanded nodes: {astar.expanded_nodes}")

    # 3) Giải bằng A* với h_zero (baseline UCS)
    print("=== A* with h_zero ===")
    astar0 = AStar(problem, h_zero)
    goal0 = astar0.solve()
    print_solution(goal0)
    print(f"Expanded nodes: {astar0.expanded_nodes}")

    # 4) So sánh nhanh với BFS
    print("=== BFS ===")
    bfs_solver = BFS(problem)
    goal_b = bfs_solver.solve()
    print_solution(goal_b)
    print(f"Expanded nodes: {bfs_solver.expanded_nodes}")

    # 5) Đánh giá heuristic — Mỗi heuristic 2 bảng:
    #    (A1/B1) Admissible dọc theo path; (A2/B2) Consistent trên K bước đầu
    K = 8

    if goal is not None:
        print("\n### Heuristic: h_pair")
        print("BẢNG A1 — Admissible (h(n) ≤ h*(n)) dọc theo đường đi nghiệm — h_pair")
        _ = evaluate_admissibility_along_path(problem, h_pair, goal)

        print(f"BẢNG A2 — Consistent (h(n) ≤ 1 + h(n')) trên {K} bước đầu — h_pair")
        _ = evaluate_consistency_along_path(problem, h_pair, goal, max_steps=K)
    else:
        print("Không có lời giải (h_pair) để đánh giá.")

    if goal0 is not None:
        print("\n### Heuristic: h_zero")
        print("BẢNG B1 — Admissible (h(n) ≤ h*(n)) dọc theo đường đi nghiệm — h_zero")
        _ = evaluate_admissibility_along_path(problem, h_zero, goal0)

        print(f"BẢNG B2 — Consistent (h(n) ≤ 1 + h(n')) trên {K} bước đầu — h_zero")
        _ = evaluate_consistency_along_path(problem, h_zero, goal0, max_steps=K)
    else:
        print("Không có lời giải (h_zero) để đánh giá.")

    # 6) Thí nghiệm nhỏ (M trạng thái sinh từ goal bằng các action hợp lệ)
    M = 8
    base_goal_problem = EightPuzzleProblem(((1,2,3),(4,5,6),(7,8,0)))
    initials = [random_state_from_goal(base_goal_problem, steps=40, seed=100+i) for i in range(M)]

    res = experiment_compare(initials)
    print("\n=== Summary (A*_h0 vs A*_hpair vs BFS) ===")
    summary = summarize_results(res)
    for name, row in summary.items():
        print(name, row)
    print_table_from_summary("So sánh A* (h0) vs A* (h_pair) vs BFS", summary)

    # 7) Render PNG với giới hạn số cạnh & đúng “n NÚT”
    DOT = None  # hoặc r"C:\Program Files\Graphviz\bin\dot.exe"
    render_search_tree_png(astar, max_edges=60, filename="search_tree_edges", dot_path=DOT)
    render_search_tree_png_by_nodes(astar, max_nodes=10, filename="search_tree_10_nodes", dot_path=DOT)
