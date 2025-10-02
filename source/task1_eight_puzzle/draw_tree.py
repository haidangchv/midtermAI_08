def draw_tree(solution_node_path, n: int, out_txt: str = "../../results/tree_task1.txt"):
    """
    Placeholder: ghi thông tin n nút đầu tiên trong đường đi lời giải ra file .txt.
    (Nhóm có thể thay thế bằng graphviz để vẽ ảnh .png)
    """
    lines = []
    for i, node in enumerate(solution_node_path[:max(1,n)]):
        lines.append(f"[{i}] g={node.g:.1f}, h={node.h:.1f}, f={node.f:.1f}, state={node.state}")
    with open(out_txt, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    return out_txt
