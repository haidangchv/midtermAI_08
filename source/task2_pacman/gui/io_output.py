from .config import PATH_TXT, OUT_TXT

def write_outputs(path_coords, actions, cost):
    with open(PATH_TXT, "w", encoding="utf-8") as f:
        for (r, c) in path_coords:
            f.write(f"{r} {c}\n")
    name_map = {
        "N":"North","S":"South","E":"East","W":"West",
        "TUL":"Stop","TUR":"Stop","TBL":"Stop","TBR":"Stop",
    }
    pretty_actions = [name_map.get(a, "West") for a in actions]
    with open(OUT_TXT, "w", encoding="utf-8") as f:
        f.write(f"cost: {int(cost) if cost == int(cost) else cost}\n")
        f.write("actions:\n")
        for act in pretty_actions:
            f.write(act + "\n")
