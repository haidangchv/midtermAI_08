# tree_tracer.py
from typing import Dict, List, Tuple
from astar import Node

class SearchTreeTracer:
    """
    Thu thập cạnh cha→con do A* sinh ra; dừng khi đủ n node generate.
    """
    def __init__(self, n_limit: int = 50):
        self.n_limit = max(1, n_limit)
        self.generated = 0
        self.edges: List[Tuple[str, str]] = []      # danh sách cạnh (u_id, v_id)
        self.id_of: Dict[int, str] = {}             # map id(state) -> label ngắn
        self._next_id = 0

    def _label(self, node: Node) -> str:
        key = id(node.state)
        if key not in self.id_of:
            self.id_of[key] = "S" if self._next_id == 0 else f"N{self._next_id}"
            self._next_id += 1
        return self.id_of[key]

    def on_generate(self, parent: Node, child: Node):
        if self.generated >= self.n_limit:
            return
        u = self._label(parent)
        v = self._label(child)
        self.edges.append((u, v))
        self.generated += 1

    def to_dot(self) -> str:
        lines = ['digraph SearchTree {', '  node [shape=circle, fontname="Arial"];']
        for u, v in self.edges:
            lines.append(f'  "{u}" -> "{v}";')
        lines.append('}')
        return "\n".join(lines)
