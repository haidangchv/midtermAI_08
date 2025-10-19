import pygame
from .config import (CELL_LOGICAL, HUD_H, COLOR_BG, COLOR_WALL, COLOR_WALL_EDGE, COLOR_FLOOR, COLOR_GRID,
                     COLOR_EXIT, COLOR_PIE, COLOR_ANCHOR, COLOR_HUD_TEXT, COLOR_HUD_EMPH)
from .layout import corner_anchors, is_at_anchor

class Renderer:
    def __init__(self, assets):
        self.assets = assets
        self.logical_surface = None

    def new_surface(self, grid):
        self.logical_surface = self._make_surface_like(grid)
        return self.logical_surface

    def _make_surface_like(self, grid):
        w = len(grid[0]) * CELL_LOGICAL
        h = len(grid) * CELL_LOGICAL + HUD_H
        surf = pygame.Surface((w, h), pygame.SRCALPHA).convert_alpha()
        surf.fill((0, 0, 0, 0))
        return surf

    def compute_scaled_rect(self, window_size):
        Ww, Hw = window_size
        Wl, Hl = self.logical_surface.get_size()
        if Wl == 0 or Hl == 0:
            return pygame.Rect(0, 0, Ww, Hw)
        scale = min(Ww / Wl, Hw / Hl)
        Tw, Th = int(Wl * scale), int(Hl * scale)
        x = (Ww - Tw) // 2
        y = (Hw - Th) // 2
        return pygame.Rect(x, y, Tw, Th)

    def present(self, screen):
        rect = self.compute_scaled_rect(screen.get_size())
        screen.fill(COLOR_BG)
        if rect.size != self.logical_surface.get_size():
            scaled = pygame.transform.smoothscale(self.logical_surface, rect.size)
            screen.blit(scaled, rect.topleft)
        else:
            screen.blit(self.logical_surface, rect.topleft)

    def update_anim(self, dt_ms: int):
        if not self.assets.pac_frames: return
        self._acc = getattr(self, "_acc", 0) + dt_ms
        if self._acc >= self.assets.pac_anim_interval_ms:
            self.assets.pac_frame_index = (self.assets.pac_frame_index + 1) % len(self.assets.pac_frame_seq)
            self._acc = 0

    def set_last_dir(self, d: int):
        self.assets.last_pac_dir = d

    def _blit_center(self, surface, img, cell_rect):
        ir = img.get_rect()
        surface.blit(img, (cell_rect.x + (cell_rect.w - ir.w)//2,
                           cell_rect.y + (cell_rect.h - ir.h)//2))

    def draw_grid(self, grid, pac, foods, exit_pos, pies, ghosts, ttl, step_mod, auto_mode, steps_count):
        surface = self.logical_surface
        surface.fill((0,0,0,0))
        R, C = len(grid), len(grid[0])
        cell = CELL_LOGICAL
        floor = pygame.Surface((cell, cell), pygame.SRCALPHA); floor.fill(COLOR_FLOOR)
        grid_edge = pygame.Surface((cell, cell), pygame.SRCALPHA)
        pygame.draw.rect(grid_edge, COLOR_GRID, pygame.Rect(0, 0, cell, cell), 1)

        # tiles & items
        for r in range(R):
            for c in range(C):
                x, y = c*cell, r*cell
                rect = pygame.Rect(x, y, cell, cell)
                ch = grid[r][c]
                if ch == '%':
                    pygame.draw.rect(surface, COLOR_WALL, rect, border_radius=2)
                    pygame.draw.rect(surface, COLOR_WALL_EDGE, rect, 1, border_radius=2)
                else:
                    surface.blit(floor, (x, y))
                    surface.blit(grid_edge, (x, y))
                if (r, c) in pies:
                    pygame.draw.circle(surface, COLOR_PIE, rect.center, cell//5)
                if (r, c) in foods:
                    self._blit_center(surface, self.assets.food_img, rect)
                if exit_pos == (r, c):
                    pygame.draw.rect(surface, COLOR_EXIT, rect, 3, border_radius=4)

        # ghosts
        color_order = ["red", "blue", "pink", "orange"]
        for i, ((gr, gc), _dir) in enumerate(ghosts):
            grect = pygame.Rect(gc*cell, gr*cell, cell, cell)
            key = color_order[i % len(color_order)]
            img = self.assets.ghost_imgs.get(key, self.assets.ghost_fallback) if self.assets.ghost_imgs else self.assets.ghost_fallback
            if img is None:
                img = pygame.Surface((cell, cell), pygame.SRCALPHA)
                pygame.draw.circle(img, (215,60,60), (cell//2, cell//2), cell//3)
            self._blit_center(surface, img, grect)

        # pacman
        prect = pygame.Rect(pac[1]*cell, pac[0]*cell, cell, cell)
        fidx = self.assets.pac_frame_seq[self.assets.pac_frame_index] if self.assets.pac_frames else 0
        base_img = self.assets.pac_frames[fidx] if self.assets.pac_frames else self.assets.pacman_img
        img = base_img
        if self.assets.last_pac_dir == 1: img = pygame.transform.flip(base_img, True, False)
        elif self.assets.last_pac_dir == 2: img = pygame.transform.rotate(base_img, 90)
        elif self.assets.last_pac_dir == 3: img = pygame.transform.rotate(base_img, 270)
        self._blit_center(surface, img, prect)

        # anchors
        anchors = corner_anchors(grid)
        font_small = pygame.font.SysFont(None, 18)
        for i, (ar, ac) in enumerate(anchors):
            arect = pygame.Rect(ac*cell, ar*cell, cell, cell)
            pygame.draw.rect(surface, COLOR_ANCHOR, arect, 2, border_radius=4)
            tag = font_small.render(str(i+1), True, COLOR_ANCHOR)
            surface.blit(tag, (arect.x + 4, arect.y + 2))

        # HUD
        font = pygame.font.SysFont(None, 20)
        y0 = cell*R + 6
        remaining = len(foods)
        hud_bg = pygame.Surface((cell*C, 84-6), pygame.SRCALPHA); hud_bg.fill((0,0,0,120))
        surface.blit(hud_bg, (0, cell*R))
        hud1 = font.render(
            f"TTL: {ttl}   step%30: {step_mod}   STEPS: {steps_count}   AUTO: {'ON' if auto_mode else 'OFF'}   FOOD LEFT: {remaining}   PAC: ({pac[0]},{pac[1]})",
            True, COLOR_HUD_TEXT
        )
        surface.blit(hud1, (8, y0))
        if is_at_anchor(grid, pac):
            hint = font.render("Teleport: Shift + 1–4 (TL, TR, BL, BR)", True, COLOR_HUD_EMPH)
            surface.blit(hint, (8, y0 + 20))
        if tuple(pac) == exit_pos and remaining > 0:
            warn = font.render(f" Need to eat more {remaining} food before EXIT!", True, (255, 210, 90))
            surface.blit(warn, (8, y0 + 40))

    def show_center_message(self, screen, text, millis=1200):
        overlay = pygame.Surface(screen.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        screen.blit(overlay, (0, 0))
        box_w, box_h = int(screen.get_width()*0.5), 120
        box_x = (screen.get_width() - box_w)//2
        box_y = (screen.get_height() - box_h)//2
        box = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(screen, (28, 28, 32), box, border_radius=12)
        pygame.draw.rect(screen, (255, 90, 90), box, 2, border_radius=12)
        font_big = pygame.font.SysFont(None, 42)
        font_small = pygame.font.SysFont(None, 22)
        msg = font_big.render(text, True, (255, 220, 220))
        hint = font_small.render("Resetting...", True, (220, 220, 220))
        screen.blit(msg, (box.centerx - msg.get_width()//2, box_y + 18))
        screen.blit(hint, (box.centerx - hint.get_width()//2, box_y + 68))
        pygame.display.flip()
        pygame.time.wait(millis)

    def draw_endgame_overlay(self, screen, steps_text=""):
        overlay = pygame.Surface(self.logical_surface.get_size(), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        box_w, box_h = int(self.logical_surface.get_width() * 0.6), 180
        box_x = (self.logical_surface.get_width() - box_w)//2
        box_y = (self.logical_surface.get_height() - box_h)//2
        box = pygame.Rect(box_x, box_y, box_w, box_h)
        pygame.draw.rect(overlay, (28, 28, 32, 240), box, border_radius=12)
        pygame.draw.rect(overlay, (80, 220, 180, 255), box, 3, border_radius=12)
        font_big = pygame.font.SysFont(None, 42)
        font_mid = pygame.font.SysFont(None, 24)
        title = font_big.render("Complete the mission!", True, (240, 240, 240))
        subtitle = font_mid.render("Press R to play again • Esc to exit", True, (210, 210, 210))
        surface = self.logical_surface
        overlay.blit(title,   (box.centerx - title.get_width()//2,   box_y + 26))
        if steps_text:
            metric_txt = font_mid.render(steps_text, True, (210, 210, 210))
            overlay.blit(metric_txt, (box.centerx - metric_txt.get_width()//2, box_y + 72))
        overlay.blit(subtitle,(box.centerx - subtitle.get_width()//2, box_y + 110))
        surface.blit(overlay, (0, 0))
