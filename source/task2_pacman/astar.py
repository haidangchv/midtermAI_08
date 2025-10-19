from heapq import heappush, heappop

class Node:
    __slots__ = ("state","g","h","parent","action")
    def __init__(self, state, g, h, parent, action):
        self.state  = state
        self.g      = g
        self.h      = h
        self.parent = parent
        self.action = action
    def f(self): return self.g + self.h

def reconstruct(node):
    states = []
    actions = []
    cur = node
    while cur is not None:
        states.append(cur.state)
        actions.append(cur.action)
        cur = cur.parent
    states.reverse()
    actions.reverse()
    if actions and actions[0] is None:  # root
        actions = actions[1:]
    return states, actions

def astar(problem, heuristic, graph_search=True, goal_fn=None, max_expanded=200000):
    """
    A* dùng problem.actions(s) + problem.result(s,a).
    Bỏ qua mọi result None. Không 'unpack' successors kiểu (s,a).
    """
    start = problem.initial_state()
    h0 = float(getattr(heuristic, "h", lambda s: 0.0)(start) or 0.0)
    root = Node(start, g=0.0, h=h0, parent=None, action=None)

    openpq = []
    heappush(openpq, (root.f(), 0, root))
    best_g = {start: 0.0} if graph_search else {}
    expanded = 0
    generated = 1
    tie = 1

    while openpq:
        if expanded > max_expanded:
            return {"solution": None, "actions": [], "cost": float("inf"),
                    "generated": generated, "expanded": expanded, "reason": "limit"}

        _, _, node = heappop(openpq)
        s = node.state

        is_goal = problem.is_goal(s) if goal_fn is None else bool(goal_fn(s))
        if is_goal:
            states, actions = reconstruct(node)
            return {"solution": states, "actions": actions, "cost": node.g,
                    "generated": generated, "expanded": expanded}

        expanded += 1
        try:
            act_list = list(problem.actions(s))
        except Exception:
            act_list = []
            
        def _prio(a):
            return 0 if a in ("TUL","TUR","TBL","TBR") else 1
        act_list.sort(key=_prio)
        
        for a in act_list:
            try:
                s2 = problem.result(s, a)
            except Exception:
                s2 = None
            if s2 is None:
                continue

            try:
                g2 = node.g + float(problem.step_cost(s, a, s2))
            except Exception:
                g2 = node.g + 1.0

            if graph_search:
                old = best_g.get(s2)
                if old is not None and g2 >= old:
                    continue
                best_g[s2] = g2

            try:
                h2 = float(getattr(heuristic, "h", lambda st: 0.0)(s2) or 0.0)
            except Exception:
                h2 = 0.0

            child = Node(s2, g2, h2, node, a)
            heappush(openpq, (child.f(), tie, child))
            tie += 1
            generated += 1

    return {"solution": None, "actions": [], "cost": float("inf"),
            "generated": generated, "expanded": expanded}
