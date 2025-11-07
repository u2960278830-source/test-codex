"""Stylized Angry Birds inspired game using pygame and pymunk.

This module exposes a :func:`main` entry point which launches the game.
"""
from __future__ import annotations

import math
import random
from dataclasses import dataclass
from typing import List, Optional, Tuple

import pygame
import pymunk
from pygame import Surface

# Screen configuration.
SCREEN_WIDTH = 1280
SCREEN_HEIGHT = 720
FPS = 60

# Colors.
SKY_TOP = (135, 206, 235)
SKY_BOTTOM = (198, 234, 255)
GROUND_COLOR = (116, 85, 62)
SUN_COLOR = (255, 238, 150)
SLING_COLOR = (139, 69, 19)
BIRD_PRIMARY = (221, 55, 55)
BIRD_SECONDARY = (240, 240, 240)
PIG_COLOR = (150, 215, 75)
BLOCK_WOOD = (196, 142, 62)
BLOCK_STEEL = (160, 170, 180)
TEXT_COLOR = (20, 20, 20)
SHADOW_COLOR = (0, 0, 0, 90)

# Physics constants.
GRAVITY = (0, 900)
GROUND_Y = SCREEN_HEIGHT - 120
SPACE_DAMPING = 0.7

# Gameplay constants.
MAX_BIRDS = 4
SLINGSHOT_POS = (180, GROUND_Y - 120)
SLINGSHOT_RADIUS = 45
MAX_DRAG_DISTANCE = 140
LAUNCH_POWER = 6.5
PIG_HEALTH = 120
BLOCK_HEALTH = 160
IMPACT_THRESHOLD = 30

@dataclass
class PhysicsSprite:
    """Base class combining a pygame surface and a pymunk body/shape."""

    body: pymunk.Body
    shape: pymunk.Shape
    sprite: Surface
    offset: Tuple[int, int] = (0, 0)

    def draw(self, surface: Surface, offset: Tuple[float, float] = (0.0, 0.0)) -> None:
        """Blit the sprite respecting the physics body's position."""
        pos = (
            int(self.body.position.x + offset[0]),
            int(self.body.position.y + offset[1]),
        )
        rect = self.sprite.get_rect(center=pos)
        rect.move_ip(self.offset)
        surface.blit(self.sprite, rect)


@dataclass
class Destructible(PhysicsSprite):
    """Sprite with hit points."""

    hp: float = 100
    destroyed: bool = False

    def apply_damage(self, amount: float) -> None:
        if self.destroyed:
            return
        self.hp -= amount
        if self.hp <= 0:
            self.destroyed = True


class Bird(Destructible):
    """Bird that the player can launch."""

    def __init__(self, space: pymunk.Space, position: Tuple[float, float]):
        mass = 5
        radius = 22
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.8
        shape.friction = 0.7
        space.add(body, shape)
        sprite = render_bird(radius)
        super().__init__(body, shape, sprite, hp=60)
        self.launched = False


class Pig(Destructible):
    def __init__(self, space: pymunk.Space, position: Tuple[float, float]):
        mass = 4
        radius = 24
        moment = pymunk.moment_for_circle(mass, 0, radius)
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Circle(body, radius)
        shape.elasticity = 0.6
        shape.friction = 0.8
        space.add(body, shape)
        sprite = render_pig(radius)
        super().__init__(body, shape, sprite, hp=PIG_HEALTH)


class Block(Destructible):
    def __init__(
        self,
        space: pymunk.Space,
        position: Tuple[float, float],
        size: Tuple[float, float],
        is_steel: bool = False,
    ):
        mass = 20 if not is_steel else 35
        width, height = size
        moment = pymunk.moment_for_box(mass, (width, height))
        body = pymunk.Body(mass, moment)
        body.position = position
        shape = pymunk.Poly.create_box(body, size)
        shape.elasticity = 0.4
        shape.friction = 0.9
        space.add(body, shape)
        sprite = render_block(size, steel=is_steel)
        hp = BLOCK_HEALTH * (1.5 if is_steel else 1.0)
        super().__init__(body, shape, sprite, hp=hp)
        self.is_steel = is_steel


class GameWorld:
    """Encapsulates the physics space and active game objects."""

    def __init__(self) -> None:
        self.space = pymunk.Space()
        self.space.gravity = GRAVITY
        self.space.damping = SPACE_DAMPING
        self.space.sleep_time_threshold = 0.3

        self.birds: List[Bird] = []
        self.pigs: List[Pig] = []
        self.blocks: List[Block] = []
        self.active_bird: Optional[Bird] = None

        self.ground_body = pymunk.Body(body_type=pymunk.Body.STATIC)
        ground_shape = pymunk.Segment(
            self.ground_body,
            (0, GROUND_Y),
            (SCREEN_WIDTH * 2, GROUND_Y),
            3,
        )
        ground_shape.elasticity = 0.6
        ground_shape.friction = 0.9
        self.space.add(self.ground_body, ground_shape)

        self._setup_collision_handlers()

    def _setup_collision_handlers(self) -> None:
        def impact_callback(arbiter: pymunk.Arbiter, _space: pymunk.Space, _data: dict) -> bool:
            impulse = arbiter.total_impulse.length
            for shape in arbiter.shapes:
                sprite = getattr(shape, "sprite_ref", None)
                if isinstance(sprite, Destructible):
                    sprite.apply_damage(impulse / IMPACT_THRESHOLD)
            return True

        handler = self.space.add_default_collision_handler()
        handler.post_solve = impact_callback

        for shape in list(self.space.shapes):
            if shape.body.body_type != pymunk.Body.STATIC:
                shape.sprite_ref = None  # type: ignore[attr-defined]

    def register_sprite(self, obj: Destructible) -> None:
        obj.shape.sprite_ref = obj  # type: ignore[attr-defined]

    def spawn_bird(self) -> None:
        if len(self.birds) >= MAX_BIRDS:
            return
        spawn_pos = (SLINGSHOT_POS[0] - 40 + len(self.birds) * 32, SLINGSHOT_POS[1] + 35)
        bird = Bird(self.space, spawn_pos)
        bird.body.body_type = pymunk.Body.KINEMATIC
        bird.body.velocity = (0, 0)
        bird.launched = False
        self.register_sprite(bird)
        self.birds.append(bird)
        if not self.active_bird:
            self.active_bird = bird

    def load_level(self) -> None:
        self.clear()
        self.spawn_bird()
        self.spawn_bird()
        self.spawn_bird()
        # Simple structure of blocks and pigs.
        base_x = 780
        base_y = GROUND_Y - 30
        for i in range(3):
            block = Block(self.space, (base_x + i * 70, base_y), (120, 30))
            self.register_sprite(block)
            self.blocks.append(block)
        pig = Pig(self.space, (base_x + 70, base_y - 70))
        self.register_sprite(pig)
        self.pigs.append(pig)
        top_block = Block(self.space, (base_x + 70, base_y - 120), (160, 30), is_steel=True)
        self.register_sprite(top_block)
        self.blocks.append(top_block)
        pig2 = Pig(self.space, (base_x + 70, base_y - 180))
        self.register_sprite(pig2)
        self.pigs.append(pig2)

    def clear(self) -> None:
        for obj_list in (self.birds, self.pigs, self.blocks):
            for obj in obj_list:
                self.space.remove(obj.body, obj.shape)
            obj_list.clear()
        self.active_bird = None

    def update(self, dt: float) -> None:
        self.space.step(dt)
        self._cleanup_destroyed()

    def _cleanup_destroyed(self) -> None:
        def filter_list(items: List[Destructible]) -> List[Destructible]:
            alive = []
            for item in items:
                if item.destroyed:
                    self.space.remove(item.body, item.shape)
                else:
                    alive.append(item)
            return alive

        for bird in list(self.birds):
            if bird.destroyed:
                self.space.remove(bird.body, bird.shape)
                self.birds.remove(bird)
        self.pigs = list(filter_list(self.pigs))
        self.blocks = list(filter_list(self.blocks))
        if self.active_bird and self.active_bird.destroyed:
            self.active_bird = None

    def next_bird(self) -> Optional[Bird]:
        ready_birds = [b for b in self.birds if not b.launched]
        self.active_bird = ready_birds[0] if ready_birds else None
        if self.active_bird:
            self.active_bird.body.body_type = pymunk.Body.KINEMATIC
            self.active_bird.body.velocity = (0, 0)
        return self.active_bird


class Game:
    def __init__(self) -> None:
        pygame.init()
        pygame.display.set_caption("PyBirds")
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 22, bold=True)
        self.big_font = pygame.font.SysFont("arial", 32, bold=True)
        self.background = render_background()
        self.background_width = self.background.get_width()
        try:
            if not pygame.mixer.get_init():
                pygame.mixer.init()
        except pygame.error:
            self.audio_enabled = False
            self.launch_sound = None
        else:
            self.audio_enabled = True
            self.launch_sound = render_launch_sound()

        self.world = GameWorld()
        self.world.load_level()
        self.camera_x = 0.0
        self.dragging = False
        self.drag_vector = (0.0, 0.0)
        self.aim_line_surface = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)

    def run(self) -> None:
        running = True
        while running:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    if event.key == pygame.K_r:
                        self.world.load_level()
                        self.camera_x = 0.0
                        self.drag_vector = (0.0, 0.0)
                        self.dragging = False
                    if event.key == pygame.K_SPACE:
                        self.world.spawn_bird()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    self.handle_mouse_down(event.pos)
                elif event.type == pygame.MOUSEBUTTONUP:
                    self.handle_mouse_up(event.pos)
                elif event.type == pygame.MOUSEMOTION:
                    self.handle_mouse_motion(event.pos)

            self.update(dt)
            self.draw()

        pygame.quit()

    def update(self, dt: float) -> None:
        if self.world.active_bird and not self.world.active_bird.launched:
            self.world.active_bird.body.position = (
                SLINGSHOT_POS[0] - self.drag_vector[0],
                SLINGSHOT_POS[1] - self.drag_vector[1],
            )
        self.world.update(dt)
        self._update_camera()
        self._retire_inactive_birds()

    def _update_camera(self) -> None:
        focus_x = SLINGSHOT_POS[0]
        if self.world.active_bird and self.world.active_bird.launched:
            focus_x = self.world.active_bird.body.position.x
        self.camera_x += (focus_x - self.camera_x - SCREEN_WIDTH / 2) * 0.04
        self.camera_x = max(0, min(self.camera_x, 600))

    def _retire_inactive_birds(self) -> None:
        for bird in self.world.birds:
            if not bird.launched:
                continue
            if bird.body.position.y > SCREEN_HEIGHT + 200 or bird.body.position.x > SCREEN_WIDTH * 2:
                bird.destroyed = True
            elif bird.body.velocity.length < 10 and abs(bird.body.position.y - GROUND_Y) < 5:
                bird.destroyed = True
        if self.world.active_bird and self.world.active_bird.destroyed:
            self.world.next_bird()

    def handle_mouse_down(self, pos: Tuple[int, int]) -> None:
        bird = self.world.active_bird
        if bird and bird.launched:
            bird = self.world.next_bird()
        if not bird:
            bird = self.world.next_bird()
        if bird and distance(pos, SLINGSHOT_POS) <= SLINGSHOT_RADIUS + 10:
            self.dragging = True

    def handle_mouse_up(self, _pos: Tuple[int, int]) -> None:
        bird = self.world.active_bird
        if self.dragging and bird and not bird.launched:
            power = min(MAX_DRAG_DISTANCE, vector_length(self.drag_vector))
            if power > 5:
                direction = normalize(self.drag_vector)
                impulse = (-direction[0] * power * LAUNCH_POWER, -direction[1] * power * LAUNCH_POWER)
                bird.body.body_type = pymunk.Body.DYNAMIC
                bird.body.apply_impulse_at_local_point(impulse)
                bird.launched = True
                if self.audio_enabled and self.launch_sound:
                    self.launch_sound.play()
            else:
                bird.body.position = SLINGSHOT_POS
        self.dragging = False
        self.drag_vector = (0.0, 0.0)

    def handle_mouse_motion(self, pos: Tuple[int, int]) -> None:
        if not self.dragging:
            return
        dx = pos[0] - SLINGSHOT_POS[0]
        dy = pos[1] - SLINGSHOT_POS[1]
        length = min(MAX_DRAG_DISTANCE, math.hypot(dx, dy))
        angle = math.atan2(dy, dx)
        self.drag_vector = (math.cos(angle) * length, math.sin(angle) * length)

    def draw(self) -> None:
        parallax_x = max(min(-self.camera_x * 0.35, 0), SCREEN_WIDTH - self.background_width)
        self.screen.blit(self.background, (int(parallax_x), 0))
        camera_offset = (-self.camera_x, 0)

        draw_ground(self.screen, camera_offset)
        draw_sun(self.screen)
        draw_slingshot(self.screen, SLINGSHOT_POS, camera_offset, self.drag_vector, self.dragging)

        self.aim_line_surface.fill((0, 0, 0, 0))
        if self.dragging and self.world.active_bird:
            draw_aim_line(
                self.aim_line_surface,
                (
                    SLINGSHOT_POS[0] + camera_offset[0],
                    SLINGSHOT_POS[1] + camera_offset[1],
                ),
                (
                    SLINGSHOT_POS[0] - self.drag_vector[0] + camera_offset[0],
                    SLINGSHOT_POS[1] - self.drag_vector[1] + camera_offset[1],
                ),
            )
        self.screen.blit(self.aim_line_surface, (0, 0))

        for block in self.world.blocks:
            draw_shadow(self.screen, block, camera_offset)
            block.draw(self.screen, camera_offset)
        for pig in self.world.pigs:
            draw_shadow(self.screen, pig, camera_offset)
            pig.draw(self.screen, camera_offset)
        for bird in self.world.birds:
            draw_shadow(self.screen, bird, camera_offset)
            bird.draw(self.screen, camera_offset)

        self._draw_ui()
        pygame.display.flip()

    def _draw_ui(self) -> None:
        pigs_remaining = len(self.world.pigs)
        text = self.font.render(f"Pigs remaining: {pigs_remaining}", True, TEXT_COLOR)
        birds_ready = len([b for b in self.world.birds if not b.launched])
        birds_text = self.font.render(f"Birds ready: {birds_ready}", True, TEXT_COLOR)
        instructions = self.font.render("Drag and release to launch. R to reset. Space for extra birds.", True, TEXT_COLOR)
        status = None
        if pigs_remaining == 0:
            status = self.big_font.render("Stage Clear!", True, (255, 215, 0))
        elif not birds_ready and self.world.active_bird and self.world.active_bird.launched:
            status = self.big_font.render("Out of birds!", True, (220, 20, 60))

        self.screen.blit(text, (20, 20))
        self.screen.blit(birds_text, (20, 50))
        self.screen.blit(instructions, (20, SCREEN_HEIGHT - 40))
        if status:
            rect = status.get_rect(center=(SCREEN_WIDTH // 2, 60))
            self.screen.blit(status, rect)


def draw_shadow(surface: Surface, obj: PhysicsSprite, offset: Tuple[float, float]) -> None:
    shadow = pygame.Surface(obj.sprite.get_size(), pygame.SRCALPHA)
    pygame.draw.ellipse(
        shadow,
        SHADOW_COLOR,
        shadow.get_rect().inflate(10, 10),
    )
    pos = int(obj.body.position.x + offset[0]), int(obj.body.position.y + offset[1])
    rect = shadow.get_rect(center=(pos[0], GROUND_Y - 4))
    surface.blit(shadow, rect)


def draw_ground(surface: Surface, offset: Tuple[float, float]) -> None:
    ground_rect = pygame.Rect(int(offset[0]), GROUND_Y + int(offset[1]), SCREEN_WIDTH * 2, SCREEN_HEIGHT - GROUND_Y)
    pygame.draw.rect(surface, GROUND_COLOR, ground_rect)
    start_x = int(offset[0]) % 50
    for x in range(-start_x - 50, SCREEN_WIDTH + 100, 50):
        pygame.draw.circle(
            surface,
            (110, 78, 55),
            (x + 25 + int(offset[0]), GROUND_Y + int(offset[1])),
            30,
        )


def draw_sun(surface: Surface) -> None:
    pygame.draw.circle(surface, SUN_COLOR, (SCREEN_WIDTH - 140, 140), 80)
    for i in range(6):
        angle = math.pi * 2 * i / 6
        start = (
            SCREEN_WIDTH - 140 + math.cos(angle) * 90,
            140 + math.sin(angle) * 90,
        )
        end = (
            SCREEN_WIDTH - 140 + math.cos(angle) * 120,
            140 + math.sin(angle) * 120,
        )
        pygame.draw.line(surface, SUN_COLOR, start, end, 4)


def draw_slingshot(
    surface: Surface,
    anchor: Tuple[int, int],
    offset: Tuple[float, float],
    drag_vector: Tuple[float, float],
    dragging: bool,
) -> None:
    anchor_x = anchor[0] + offset[0]
    anchor_y = anchor[1] + offset[1]
    base_pos = (anchor_x, GROUND_Y + offset[1])
    pygame.draw.rect(surface, SLING_COLOR, (anchor_x - 12, base_pos[1] - 90, 12, 90), border_radius=6)
    pygame.draw.rect(surface, SLING_COLOR, (anchor_x + 10, base_pos[1] - 120, 14, 120), border_radius=6)
    pygame.draw.circle(surface, SLING_COLOR, (int(anchor_x + 18), int(base_pos[1] - 120)), 16)
    if dragging:
        pouch_pos = (int(anchor_x - drag_vector[0]), int(anchor_y - drag_vector[1]))
        pygame.draw.line(surface, (70, 40, 20), (anchor_x - 10, anchor_y - 10), pouch_pos, 6)
        pygame.draw.line(surface, (70, 40, 20), (anchor_x + 16, anchor_y - 10), pouch_pos, 6)


def draw_aim_line(surface: Surface, start: Tuple[int, int], end: Tuple[int, int]) -> None:
    points = []
    vx = (end[0] - start[0]) / 12.0
    vy = (end[1] - start[1]) / 12.0
    for i in range(1, 13):
        x = start[0] + vx * i
        y = start[1] + vy * i + i * i * 0.7
        points.append((x, y))
    for p in points:
        pygame.draw.circle(surface, (255, 255, 255, 160), (int(p[0]), int(p[1])), max(2, 6 - len(points) // 4))


def render_background() -> Surface:
    width = SCREEN_WIDTH + 600
    surface = pygame.Surface((width, SCREEN_HEIGHT))
    for y in range(SCREEN_HEIGHT):
        ratio = y / SCREEN_HEIGHT
        r = int(SKY_TOP[0] * (1 - ratio) + SKY_BOTTOM[0] * ratio)
        g = int(SKY_TOP[1] * (1 - ratio) + SKY_BOTTOM[1] * ratio)
        b = int(SKY_TOP[2] * (1 - ratio) + SKY_BOTTOM[2] * ratio)
        pygame.draw.line(surface, (r, g, b), (0, y), (width, y))
    draw_clouds(surface)
    return surface


def draw_clouds(surface: Surface) -> None:
    cloud_color = (255, 255, 255)
    random.seed(42)
    for i in range(6):
        base_x = random.randint(60, surface.get_width() - 200)
        base_y = random.randint(80, 240)
        for j in range(4):
            offset_x = random.randint(-20, 20)
            offset_y = random.randint(-10, 10)
            radius = random.randint(35, 55)
            pygame.draw.circle(surface, cloud_color, (base_x + offset_x + j * 30, base_y + offset_y), radius)


def render_bird(radius: int) -> Surface:
    surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = (radius * 2, radius * 2)
    pygame.draw.circle(surface, BIRD_PRIMARY, center, radius)
    pygame.draw.circle(surface, BIRD_SECONDARY, (center[0] - radius // 2, center[1] - radius // 3), radius // 2)
    pygame.draw.circle(surface, (0, 0, 0), (center[0] - radius // 2 + 4, center[1] - radius // 3), radius // 6)
    beak_points = [
        (center[0] + radius - 4, center[1] + 2),
        (center[0] + radius + 18, center[1] - 6),
        (center[0] + radius + 4, center[1] + 12),
    ]
    pygame.draw.polygon(surface, (250, 180, 0), beak_points)
    pygame.draw.circle(surface, (180, 0, 0), (center[0] - radius // 2, center[1] + radius // 2), radius // 4)
    return surface


def render_pig(radius: int) -> Surface:
    surface = pygame.Surface((radius * 4, radius * 4), pygame.SRCALPHA)
    center = (radius * 2, radius * 2)
    pygame.draw.circle(surface, PIG_COLOR, center, radius)
    pygame.draw.circle(surface, (255, 255, 255), (center[0] - radius // 2, center[1] - radius // 3), radius // 2)
    pygame.draw.circle(surface, (255, 255, 255), (center[0] + radius // 3, center[1] - radius // 3), radius // 2)
    pygame.draw.circle(surface, (20, 20, 20), (center[0] - radius // 2 + 4, center[1] - radius // 3), radius // 6)
    pygame.draw.circle(surface, (20, 20, 20), (center[0] + radius // 3 + 4, center[1] - radius // 3), radius // 6)
    pygame.draw.circle(surface, (110, 170, 50), (center[0], center[1] + 10), radius // 2)
    pygame.draw.circle(surface, (40, 60, 30), (center[0] - 8, center[1] + 8), radius // 8)
    pygame.draw.circle(surface, (40, 60, 30), (center[0] + 8, center[1] + 8), radius // 8)
    return surface


def render_block(size: Tuple[float, float], steel: bool = False) -> Surface:
    width, height = int(size[0]), int(size[1])
    surface = pygame.Surface((width, height), pygame.SRCALPHA)
    color = BLOCK_STEEL if steel else BLOCK_WOOD
    pygame.draw.rect(surface, color, (0, 0, width, height), border_radius=6)
    highlight = (min(color[0] + 40, 255), min(color[1] + 40, 255), min(color[2] + 40, 255))
    pygame.draw.line(surface, highlight, (6, 6), (width - 6, 6), 4)
    pygame.draw.line(surface, (60, 60, 60), (4, height - 6), (width - 4, height - 6), 3)
    return surface


def render_launch_sound() -> pygame.mixer.Sound:
    sample_rate = 22050
    duration = 0.15
    frequency = 320
    num_samples = int(duration * sample_rate)
    volume = 2000
    samples = bytearray()
    for i in range(num_samples):
        t = i / sample_rate
        value = int(volume * math.sin(2 * math.pi * frequency * t) * (1 - t))
        samples += value.to_bytes(2, byteorder="little", signed=True)
    return pygame.mixer.Sound(buffer=bytes(samples))


def normalize(vec: Tuple[float, float]) -> Tuple[float, float]:
    length = vector_length(vec)
    if length == 0:
        return (0.0, 0.0)
    return (vec[0] / length, vec[1] / length)


def vector_length(vec: Tuple[float, float]) -> float:
    return math.hypot(vec[0], vec[1])


def distance(a: Tuple[float, float], b: Tuple[float, float]) -> float:
    return math.hypot(a[0] - b[0], a[1] - b[1])


def main() -> None:
    Game().run()


if __name__ == "__main__":
    main()
