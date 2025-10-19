from .layout import corner_anchors, move_ghosts, rotate_world
from .render import Renderer

class ActionExecutor:
    def __init__(self, renderer: Renderer):
        self.r = renderer

    def apply_action_step(self, a, grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, screen):
        """
        Thực thi 1 action (N/S/E/W hoặc TUL/TUR/TBL/TBR) với tick ma + rotate mỗi 30 bước.
        ĐÂM TƯỜNG/teleport không hợp lệ -> NO-OP (không tăng bước/cost).
        Trả về: ..., died(bool), rotated(bool)
        """
        R, C = len(grid), len(grid[0])
        prev_r, prev_c = pac[0], pac[1]
        nr, nc = prev_r, prev_c

        if a in ("N","S","E","W"):
            drdc = {"N":(-1,0),"S":(1,0),"W":(0,-1),"E":(0,1)}
            dr, dc = drdc[a]
            tr, tc = nr + dr, nc + dc

            if not (0 <= tr < R and 0 <= tc < C):
                return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, False, False

            if grid[tr][tc] == '%':
                if ttl > 0:
                    row = list(grid[tr])
                    row[tc] = ' '
                    grid[tr] = ''.join(row)
                else:
                    return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, False, False

            nr, nc = tr, tc
            self.r.set_last_dir({"E":0, "W":1, "N":2, "S":3}[a])

        elif a in ("TUL","TUR","TBL","TBR"):
            anchors = corner_anchors(grid)
            if tuple(pac) not in set(anchors):
                return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, False, False
            idx = {"TUL":0,"TUR":1,"TBL":2,"TBR":3}[a]
            nr, nc = anchors[idx]
        else:
            return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, False, False

        # tick
        pac = [nr, nc]
        step_mod = (step_mod + 1) % 30
        ttl = max(0, ttl - 1)

        if tuple(pac) in foods:
            foods.remove(tuple(pac))
        if tuple(pac) in pies:
            ttl = 5
            pies.remove(tuple(pac))

        # Va chạm trước tick
        for (gr,gc), _d in ghosts:
            if (gr,gc) == tuple(pac) and ttl == 0:
                self.r.show_center_message(screen, "Haunted by a ghost!")
                return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, True, False

        old_ghosts = ghosts
        ghosts = move_ghosts(grid, ghosts)

        # Sau tick + kiểm tra swap
        for (old_pos, _d1), (new_pos, _d2) in zip(old_ghosts, ghosts):
            if new_pos == tuple(pac):
                self.r.show_center_message(screen, "Haunted by a ghost!")
                return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, True, False
            if old_pos == (nr, nc) and new_pos == (prev_r, prev_c):
                self.r.show_center_message(screen, "Haunted by a ghost!")
                return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, True, False

        rotated = False
        if step_mod == 0:
            grid, pac_t, foods, pies, ghosts, exit_pos = rotate_world(
                grid, tuple(pac), foods, pies, ghosts, exit_pos
            )
            pac = list(pac_t)
            self.r.new_surface(grid)
            rotated = True

        return grid, pac, foods, pies, ghosts, exit_pos, ttl, step_mod, False, rotated
