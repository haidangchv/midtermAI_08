from __future__ import annotations
from typing import Any, Iterable, Protocol, Tuple, Optional, Dict, List
import heapq

class Problem(Protocol):
    def initial_state(self) -> Any: ...
    def is_goal(self, state: Any) -> bool: ...
    def actions(self, state: Any) -> Iterable[Any]: ...
    def result(self, state: Any, action: Any) -> Any: ...
    def step_cost(self, state: Any, action: Any, next_state: Any) -> float: ...

class Heuristic(Protocol):
    def h(self, state: Any) -> float: ...

class Node:
    __slots__ = ("state","g","h","f","parent","action")
    def __init__(self, state: Any, g: float, h: float, parent: Optional["Node"]=None, action: Any=None):
        self.state = state; self.g = g; self.h = h; self.f = g + h
        self.parent = parent; self.action = action

    def path(self) -> List["Node"]:
        n, out = self, []
        while n: out.append(n); n = n.parent
        return list(reversed(out))

def astar(problem: Problem, heuristic: Heuristic, *, graph_search: bool=True):
    start = problem.initial_state()
    root = Node(start, 0.0, heuristic.h(start))
    open_heap: List[Tuple[float,int,Node]] = []; tie = 0
    heapq.heappush(open_heap, (root.f, tie, root))
    best_g: Dict[Any, float] = {start: 0.0} if graph_search else {}
    expanded = generated = 0

    while open_heap:
        _,_, node = heapq.heappop(open_heap); expanded += 1
        if problem.is_goal(node.state):
            return {"solution": node.path(), "expanded": expanded, "generated": generated, "cost": node.g}
        for action in problem.actions(node.state):
            s2 = problem.result(node.state, action)
            if s2 is None:
                # trạng thái không hợp lệ (ví dụ: đụng ma) -> bỏ qua
                continue
            
            g2 = node.g + problem.step_cost(node.state, action, s2)
            
            if graph_search and g2 >= best_g.get(s2, float("inf")) - 1e-12: continue
            
            h2 = heuristic.h(s2); n2 = Node(s2, g2, h2, node, action); generated += 1
            if graph_search: best_g[s2] = g2
            tie += 1; heapq.heappush(open_heap, (n2.f, tie, n2))
    return {"solution": None, "expanded": expanded, "generated": generated, "cost": float("inf")}
