import pygame
import math
import sys
import random

# -------------------------------------------------
# INITIALIZATION
# -------------------------------------------------
pygame.init()
pygame.mixer.init(frequency=22050, size=-16, channels=2, buffer=512)

WIDTH, HEIGHT = 800, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("Zig-Zag Racer")

# Colors
ROAD_COLOR = (50, 50, 60)
OFFROAD_COLOR = (34, 139, 34)
LINE_COLOR = (255, 255, 255)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
YELLOW = (255, 255, 0)
GRAY = (100, 100, 100)

# -------------------------------------------------
# GAME SETTINGS
# -------------------------------------------------
BASE_SPEED = 5.0
STEER_SPEED = 3.5
OFFROAD_FRICTION = 0.6
ROAD_WIDTH = 180
CHECKPOINT_DISTANCE = 800  # every 800px
MAX_OFFROAD_TIME = 2.0     # seconds before game over
DRIFT_THRESHOLD = 2.0      # speed difference to trigger skid

# -------------------------------------------------
# CAR CLASS
# -------------------------------------------------
class Car:
    def __init__(self, x, y, color, is_player=False):
        self.x = x
        self.y = y
        self.angle = 0
        self.speed = 0
        self.max_speed = BASE_SPEED
        self.color = color
        self.is_player = is_player
        self.drift = 0
        self.offroad_timer = 0
        self.checkpoints = 0
        self.lap = 0
        self.alive = True

        # Load or create car sprite
        self.base_surf = pygame.Surface((36, 58), pygame.SRCALPHA)
        pygame.draw.rect(self.base_surf, color, (0, 0, 36, 58))
        pygame.draw.rect(self.base_surf, WHITE, (0, 0, 36, 58), 3)

    def update(self, keys, road_mask, scroll_y, dt):
        if not self.alive:
            return

        rad = math.radians(self.angle)
        forward_speed = self.max_speed

        # --- INPUT ---
        if self.is_player:
            steer = 0
            if keys[pygame.K_LEFT] or keys[pygame.K_a]:
                steer -= STEER_SPEED
            if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
                steer += STEER_SPEED
            self.angle += steer
        else:
            # AI: follow road center
            self.angle += random.uniform(-1, 1)

        # --- ON/OFF ROAD ---
        wx = int(self.x - WIDTH)
        wy = int(self.y - scroll_y)
        on_road = False
        if 0 <= wx < road_mask.get_size()[0] and 0 <= wy < road_mask.get_size()[1]:
            if road_mask.get_at((wx, wy)):
                on_road = True

        if on_road:
            self.offroad_timer = 0
            forward_speed = self.max_speed
        else:
            forward_speed *= OFFROAD_FRICTION
            self.offroad_timer += dt
            if self.offroad_timer > MAX_OFFROAD_TIME:
                self.alive = False

        # --- DRIFTING ---
        lateral_speed = abs(self.speed - forward_speed)
        self.drift = lateral_speed > DRIFT_THRESHOLD

        # --- MOVEMENT ---
        old_x, old_y = self.x, self.y
        self.x += math.sin(rad) * forward_speed
        self.y += math.cos(rad) * forward_speed
        self.speed = forward_speed

        # --- COLLISION WITH ROAD EDGES ---
        rotated = pygame.transform.rotate(self.base_surf, self.angle)
        mask = pygame.mask.from_surface(rotated)
        rect = rotated.get_rect(center=(self.x, self.y))
        test_offset = (rect.x - WIDTH, rect.y - scroll_y)

        if mask.overlap(road_mask, test_offset):
            pass  # on road
        else:
            self.x, self.y = old_x, old_y  # revert

        # --- CHECKPOINTS ---
        if self.y < scroll_y - CHECKPOINT_DISTANCE * self.checkpoints:
            self.checkpoints += 1
            if self.checkpoints % 5 == 0:
                self.lap += 1

    def draw(self, surface, scroll_y):
        if not self.alive:
            return
        rotated = pygame.transform.rotate(self.base_surf, self.angle)
        rect = rotated.get_rect(center=(self.x, self.y - scroll_y))
        surface.blit(rotated, rect.topleft)
        if self.drift:
            pygame.draw.rect(surface, YELLOW, rect, 3)

# -------------------------------------------------
# PARTICLE SYSTEM
# -------------------------------------------------
particles = []

def create_smoke(x, y, scroll_y):
    for _ in range(3):
        p = {
            'x': x + random.randint(-15, 15),
            'y': y - scroll_y + random.randint(-10, 10),
            'vx': random.uniform(-1, 1),
            'vy': random.uniform(-2, -0.5),
            'life': random.randint(20, 40),
            'color': (200, 200, 200, 180)
        }
        particles.append(p)

def update_particles(dt):
    for p in particles[:]:
        p['x'] += p['vx']
        p['y'] += p['vy']
        p['vy'] += 0.05
        p['life'] -= 1
        if p['life'] <= 0:
            particles.remove(p)

def draw_particles(surface):
    for p in particles:
        alpha = int(255 * (p['life'] / 40))
        color = (*p['color'][:3], alpha)
        s = pygame.Surface((10, 10), pygame.SRCALPHA)
        pygame.draw.circle(s, color, (5, 5), 5)
        surface.blit(s, (p['x'] - 5, p['y'] - 5))

# -------------------------------------------------
# ROAD SETUP
# -------------------------------------------------
road_segments = [
    (WIDTH//2, 800, 600, 0),
    (0, 0, 300, -25),
    (0, 0, 400, 20),
    (0, 0, 350, -15),
    (0, 0, 500, 30),
    (0, 0, 400, -20),
    (0, 0, 600, 0),
]

road_points_left, road_points_right = [], []
current_x = road_segments[0][0]
current_y = road_segments[0][1]
current_angle = road_segments[0][3]

for i, (sx, sy, length, angle) in enumerate(road_segments):
    if i > 0:
        current_x = road_points_left[-1][0] if road_points_left else sx
        current_y = road_points_left[-1][1] if road_points_left else sy
        current_angle = angle

    rad = math.radians(current_angle)
    dx = math.cos(rad) * length
    dy = math.sin(rad) * length

    end_x = current_x + dx
    end_y = current_y + dy

    perp_x = -math.sin(rad) * (ROAD_WIDTH // 2)
    perp_y = math.cos(rad) * (ROAD_WIDTH // 2)

    left_x = current_x + perp_x
    left_y = current_y + perp_y
    right_x = current_x - perp_x
    right_y = current_y - perp_y

    road_points_left.append((left_x, left_y))
    road_points_right.append((right_x, right_y))

    current_x, current_y = end_x, end_y

road_polygon = road_points_left + road_points_right[::-1]

# Big surface for road
road_surface = pygame.Surface((WIDTH*3, 10000), pygame.SRCALPHA)
road_surface.fill((0,0,0,0))
offset_x = WIDTH
for i in range(0, len(road_polygon), 20):
    pts = [(x - offset_x, y) for x, y in road_polygon[i:i+20]]
    if len(pts) > 1:
        pygame.draw.polygon(road_surface, ROAD_COLOR, pts)

# Center lines
for i in range(0, len(road_points_left), 10):
    x1, y1 = road_points_left[i]
    if i+1 < len(road_points_left):
        x2, y2 = road_points_left[i+1]
        pygame.draw.line(road_surface, LINE_COLOR, (x1 - offset_x, y1), (x2 - offset_x, y2), 4)

road_mask = pygame.mask.from_surface(road_surface)

# -------------------------------------------------
# GAME STATE
# -------------------------------------------------
player = Car(WIDTH//2, HEIGHT-120, (0, 100, 255), is_player=True)
ai = Car(WIDTH//2 + 50, HEIGHT-120, (255, 50, 50), is_player=False)
scroll_y = 0
game_state = "MENU"  # MENU, PLAYING, GAMEOVER
start_time = 0
score = 0
font = pygame.font.SysFont(None, 48)
small_font = pygame.font.SysFont(None, 36)

# Sounds
try:
    engine_sound = pygame.mixer.Sound('assets/engine.wav')
    skid_sound = pygame.mixer.Sound('assets/skid.wav')
    engine_sound.play(-1)
    engine_sound.set_volume(0.3)
except:
    engine_sound = skid_sound = None

# Mobile touch
left_touch = right_touch = False

# -------------------------------------------------
# MAIN LOOP
# -------------------------------------------------
clock = pygame.time.Clock()
running = True

while running:
    dt = clock.tick(60) / 1000.0
    current_time = pygame.time.get_ticks() / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        if event.type == pygame.KEYDOWN:
            if game_state == "MENU" and event.key == pygame.K_SPACE:
                game_state = "PLAYING"
                start_time = current_time
                player.checkpoints = ai.checkpoints = 0
                player.lap = ai.lap = 0
                player.alive = ai.alive = True
            if game_state == "GAMEOVER" and event.key == pygame.K_r:
                game_state = "MENU"
        if event.type == pygame.FINGERDOWN or event.type == pygame.MOUSEBUTTONDOWN:
            x = event.x * WIDTH if hasattr(event, 'x') else pygame.mouse.get_pos()[0]
            if x < WIDTH // 2:
                left_touch = True
            else:
                right_touch = True
        if event.type == pygame.FINGERUP or event.type == pygame.MOUSEBUTTONUP:
            left_touch = right_touch = False

    keys = pygame.key.get_pressed()
    if left_touch: keys = list(keys); keys[pygame.K_LEFT] = 1
    if right_touch: keys = list(keys); keys[pygame.K_RIGHT] = 1

    # --- MENU ---
    if game_state == "MENU":
        screen.fill((20, 20, 40))
        title = font.render("ZIG-ZAG RACER", True, YELLOW)
        inst = small_font.render("Press SPACE to Start", True, WHITE)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 200))
        screen.blit(inst, (WIDTH//2 - inst.get_width()//2, 300))
        pygame.display.flip()
        continue

    # --- GAME OVER ---
    if not player.alive and game_state == "PLAYING":
        game_state = "GAMEOVER"

    if game_state == "GAMEOVER":
        screen.fill((0, 0, 0))
        over = font.render("GAME OVER", True, RED)
        restart = small_font.render("Press R to Restart", True, WHITE)
        final = small_font.render(f"Final Lap: {player.lap}  Time: {current_time - start_time:.1f}s", True, WHITE)
        screen.blit(over, (WIDTH//2 - over.get_width()//2, 200))
        screen.blit(final, (WIDTH//2 - final.get_width()//2, 280))
        screen.blit(restart, (WIDTH//2 - restart.get_width()//2, 340))
        pygame.display.flip()
        continue

    # --- UPDATE ---
    player.update(keys, road_mask, scroll_y, dt)
    ai.update(keys, road_mask, scroll_y, dt)

    # Scroll
    target_scroll = player.y - (HEIGHT - 150)
    scroll_y += (target_scroll - scroll_y) * 0.1

    # Particles
    if player.drift:
        create_smoke(player.x, player.y, scroll_y)
    update_particles(dt)

    # --- DRAW ---
    screen.fill(OFFROAD_COLOR)

    # Road
    src_y = int(scroll_y)
    road_clip = pygame.Rect(0, src_y, WIDTH, HEIGHT)
    screen.blit(road_surface, (0, 0), area=road_clip)

    # Cars
    player.draw(screen, scroll_y)
    ai.draw(screen, scroll_y)

    # Particles
    draw_particles(screen)

    # HUD
    timer = current_time - start_time
    hud = [
        f"Time: {timer:.1f}s",
        f"Lap: {player.lap}",
        f"Checkpoints: {player.checkpoints}",
        f"Speed: {player.speed:.1f}",
    ]
    for i, text in enumerate(hud):
        label = small_font.render(text, True, WHITE)
        screen.blit(label, (10, 10 + i * 30))

    # Mobile controls hint
    if pygame.display.get_surface().get_size()[0] < 500:
        pygame.draw.circle(screen, (255,255,255,100), (60, HEIGHT-60), 50, 3)
        pygame.draw.circle(screen, (255,255,255,100), (WIDTH-60, HEIGHT-60), 50, 3)

    pygame.display.flip()

    # Skid sound
    if player.drift and skid_sound:
        if not pygame.mixer.Channel(1).get_busy():
            pygame.mixer.Channel(1).play(skid_sound, loops=-1)
    elif pygame.mixer.Channel(1).get_busy():
        pygame.mixer.Channel(1).fadeout(200)

pygame.quit()
sys.exit()
