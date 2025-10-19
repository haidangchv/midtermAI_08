import os, pygame
from .config import ASSETS_DIR, SPRITE_SIZE, COLOR_FOOD

def _first_exist(paths):
    for p in paths:
        if os.path.isfile(p):
            return p
    return None

def _load_img(path, size):
    surf = pygame.image.load(path)
    if pygame.display.get_surface():
        try: surf = surf.convert_alpha()
        except pygame.error: pass
    return pygame.transform.smoothscale(surf, (size, size))

class AssetManager:
    def __init__(self):
        self.pacman_img = None
        self.food_img = None
        self.ghost_imgs = {}
        self.ghost_fallback = None
        self.pac_frames = []
        self.pac_frame_seq = [0,1,2,3,2,1]
        self.pac_frame_index = 0
        self.pac_anim_interval_ms = 90
        self.last_pac_dir = 0  # 0=E,1=W,2=N,3=S

    def load_sprite_pac(self):
        cand = [
            os.path.join(ASSETS_DIR, "pacman.png"),
            os.path.join(ASSETS_DIR, "Pacman.png"),
            os.path.join(ASSETS_DIR, "player.png"),
            os.path.join(ASSETS_DIR, "pac.png"),
        ]
        p = _first_exist(cand)
        if p: return _load_img(p, SPRITE_SIZE)
        surf = pygame.Surface((SPRITE_SIZE, SPRITE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(surf, (255,205,0), (SPRITE_SIZE//2, SPRITE_SIZE//2), SPRITE_SIZE//2 - 2)
        return surf

    def load_sprite_food(self):
        cand = [
            os.path.join(ASSETS_DIR, "food_images", "food.png"),
            os.path.join(ASSETS_DIR, "food.png"),
            os.path.join(ASSETS_DIR, "dot.png"),
        ]
        p = _first_exist(cand)
        if p:
            return _load_img(p, max(8, int(SPRITE_SIZE)))
        size = max(8, int(SPRITE_SIZE * 0.25))
        surf = pygame.Surface((size, size), pygame.SRCALPHA)
        pygame.draw.circle(surf, COLOR_FOOD, (size//2, size//2), size//2)
        return surf

    def load_sprite_ghosts(self, strict=False):
        names = ["red", "blue", "orange", "pink"]
        base_dir = os.path.join(ASSETS_DIR, "ghost_images")
        imgs = {}; missing=[]
        for name in names:
            p = os.path.join(base_dir, f"{name}.png")
            if os.path.isfile(p): imgs[name] = _load_img(p, SPRITE_SIZE)
            else: missing.append(p)
        if missing and strict:
            raise FileNotFoundError("Thiếu ảnh ghost:\n" + "\n".join(f" - {m}" for m in missing))
        fallback_paths = [
            os.path.join(ASSETS_DIR, "ghost.png"),
            os.path.join(ASSETS_DIR, "Ghost.png"),
            os.path.join(ASSETS_DIR, "enemy.png"),
        ]
        fp = _first_exist(fallback_paths)
        fb_img = _load_img(fp, SPRITE_SIZE) if fp else None
        return imgs, fb_img

    def load_pac_frames_from_player_images(self):
        cand_dirs = [
            os.path.join(ASSETS_DIR, "player_images"),
            os.path.join(ASSETS_DIR, "pacman_images"),
        ]
        names = ["1.png", "2.png", "3.png", "4.png"]
        for d in cand_dirs:
            if all(os.path.isfile(os.path.join(d, n)) for n in names):
                return [_load_img(os.path.join(d, n), SPRITE_SIZE) for n in names]
        base = self.pacman_img if self.pacman_img is not None else self.load_sprite_pac()
        return [base, base, base, base]

    def ensure_loaded(self):
        if self.pacman_img is None: self.pacman_img = self.load_sprite_pac()
        if self.food_img   is None: self.food_img   = self.load_sprite_food()
        if not self.ghost_imgs or self.ghost_fallback is None:
            self.ghost_imgs, self.ghost_fallback = self.load_sprite_ghosts(strict=False)
        if not self.pac_frames:
            self.pac_frames = self.load_pac_frames_from_player_images()
            self.pac_frame_index = 0
