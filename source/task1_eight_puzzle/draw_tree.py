def draw_tree(solution_node_path, n: int, out_txt: str = "../../results/tree_task1.txt"):
    lines = []
    for i, node in enumerate(solution_node_path[:max(1,n)]):
        g = getattr(node, "g", getattr(node, "g", 0))
        h = getattr(node, "h", 0)
        f = g + (h if isinstance(h,(int,float)) else 0)
        lines.append(f"[{i}] g={g}, h={h}, f={f}, state={node.state}")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_txt
