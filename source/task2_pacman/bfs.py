from __future__ import annotations
from typing import Any, Dict, Deque
from collections import deque

def bfs(problem, *, graph_search: bool=True):
    start = problem.initial_state()
    Node = lambda state, parent, action, g: {"state": state, "parent": parent, "action": action, "g": g}
    root = Node(start, None, None, 0)

    if problem.is_goal(start):
        return {"solution":[root], "expanded":0, "generated":0, "max_frontier":1, "cost":0}

    frontier: Deque[dict] = deque([root])
    visited: Dict[Any,int] = {start: 0} if graph_search else {}

    expanded = generated = 0
    max_frontier = len(frontier)

    while frontier:
        if len(frontier) > max_frontier:
            max_frontier = len(frontier)

        node = frontier.popleft()
        expanded += 1
        s = node["state"]

        for action in problem.actions(s):
            s2 = problem.result(s, action)
            if s2 is None:
                continue
            if graph_search and s2 in visited:
                continue
            g2 = node["g"] + problem.step_cost(s, action, s2)
            n2 = Node(s2, node, action, g2); generated += 1

            if problem.is_goal(s2):
                path=[]; cur=n2
                while cur: path.append(cur); cur=cur["parent"]
                path.reverse()
                return {"solution":path, "expanded":expanded, "generated":generated,
                        "max_frontier":max_frontier, "cost":g2}

            if graph_search: visited[s2] = g2
            frontier.append(n2)

    return {"solution":None, "expanded":expanded, "generated":generated,
            "max_frontier":max_frontier, "cost":float("inf")}
