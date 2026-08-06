from __future__ import annotations

import math
from dataclasses import dataclass

import pygame  # type: ignore[import-not-found]
from pygame import Surface

from .models import Colors, ZoneType
from .simulation import Simulation


@dataclass
class Camera:
    zoom: float = 1.0
    pan_x: float = 0.0
    pan_y: float = 0.0
    drag: bool = False
    mx: int = 0
    my: int = 0


class PygameVisualizer:
    def __init__(
        self,
        simulation: Simulation,
        drone_image_path: str = "assets/drone.png",
    ) -> None:
        self.sim = simulation
        self.drone_image_path = drone_image_path
        self.camera = Camera()

    def _zone_color(self, color_name: str | None) -> tuple[int, int, int]:
        if color_name is None:
            return (150, 150, 150)
        if color_name == "rainbow":
            arr = [
                Colors.red.value,
                Colors.orange.value,
                Colors.yellow.value,
                Colors.green.value,
                Colors.blue.value,
                Colors.indigo.value,
                Colors.violet.value,
            ]
            idx = (pygame.time.get_ticks() // 120) % len(arr)
            return arr[idx]
        if color_name in Colors.__members__:
            return Colors[color_name].value
        return (150, 150, 150)

    def _draw_glow(self, screen: Surface, x: float, y: float, c: tuple[int, int, int], r: float) -> None:
        layer = Surface(screen.get_size(), pygame.SRCALPHA)
        for rad, alpha in ((r * 2.3, 25), (r * 1.7, 45), (r * 1.3, 65)):
            pygame.draw.circle(layer, (c[0], c[1], c[2], alpha), (x, y), rad)
        screen.blit(layer, (0, 0))

    def run(self, turn_log: list[str], width: int = 1200, height: int = 900) -> None:
        pygame.init()
        screen = pygame.display.set_mode((width, height))
        pygame.display.set_caption("Fly-in / RRT* Visualizer")
        clock = pygame.time.Clock()
        font = pygame.font.SysFont("Arial", 16)

        sprite = pygame.image.load(self.drone_image_path).convert_alpha()

        zones = self.sim.zones
        min_x = min(z.x for z in zones.values())
        max_x = max(z.x for z in zones.values())
        min_y = min(z.y for z in zones.values())
        max_y = max(z.y for z in zones.values())

        cols = max_x - min_x + 2
        rows = max_y - min_y + 2

        base_w = width / cols
        base_h = height / rows

        auto = True
        timer = 0.0
        interval = 0.4
        turn_ix = 0

        running = True
        while running:
            dt = clock.tick(60) / 1000.0

            for ev in pygame.event.get():
                if ev.type == pygame.QUIT:
                    running = False
                elif ev.type == pygame.KEYDOWN:
                    if ev.key == pygame.K_ESCAPE:
                        running = False
                    elif ev.key == pygame.K_p:
                        auto = not auto
                    elif ev.key == pygame.K_SPACE:
                        if turn_ix < len(turn_log):
                            self.sim.step()
                            turn_ix += 1
                    elif ev.key in (pygame.K_PLUS, pygame.K_EQUALS):
                        interval = max(0.05, interval - 0.05)
                    elif ev.key == pygame.K_MINUS:
                        interval = min(3.0, interval + 0.05)
                elif ev.type == pygame.MOUSEWHEEL:
                    self.camera.zoom = max(0.2, min(4.0, self.camera.zoom + 0.1 * ev.y))
                elif ev.type == pygame.MOUSEBUTTONDOWN and ev.button == 1:
                    self.camera.drag = True
                    self.camera.mx, self.camera.my = ev.pos
                elif ev.type == pygame.MOUSEBUTTONUP and ev.button == 1:
                    self.camera.drag = False
                elif ev.type == pygame.MOUSEMOTION and self.camera.drag:
                    x, y = ev.pos
                    self.camera.pan_x += x - self.camera.mx
                    self.camera.pan_y += y - self.camera.my
                    self.camera.mx, self.camera.my = x, y

            if auto and turn_ix < len(turn_log):
                timer += dt
                if timer >= interval:
                    timer = 0.0
                    self.sim.step()
                    turn_ix += 1

            cw = base_w * self.camera.zoom
            ch = base_h * self.camera.zoom
            r = max(5.0, min(cw, ch) * 0.28)
            ox = (width - cols * cw) / 2 + cw + self.camera.pan_x
            oy = (height - rows * ch) / 2 + ch + self.camera.pan_y

            screen.fill((255, 255, 255))

            for c in self.sim.connections:
                a = zones[c.a]
                b = zones[c.b]
                ax = ox + (a.x - min_x) * cw
                ay = oy + (a.y - min_y) * ch
                bx = ox + (b.x - min_x) * cw
                by = oy + (b.y - min_y) * ch
                pygame.draw.line(screen, (210, 210, 210), (ax, ay), (bx, by), 5)
                pygame.draw.line(screen, (110, 140, 180), (ax, ay), (bx, by), 2)

            for z in zones.values():
                x = ox + (z.x - min_x) * cw
                y = oy + (z.y - min_y) * ch
                col = self._zone_color(z.color)

                self._draw_glow(screen, x, y, col, r)
                pygame.draw.circle(screen, (20, 20, 20), (x, y), r + 3)
                pygame.draw.circle(screen, col, (x, y), r)

                if z.zone_type == ZoneType.BLOCKED:
                    pygame.draw.line(screen, (0, 0, 0), (x - 8, y - 8), (x + 8, y + 8), 3)
                    pygame.draw.line(screen, (0, 0, 0), (x + 8, y - 8), (x - 8, y + 8), 3)

                label = font.render(z.name, True, (35, 35, 35))
                screen.blit(label, (x - label.get_width() / 2, y + r + 6))

            icon_size = max(16, int(r * 1.8))
            icon = pygame.transform.smoothscale(sprite, (icon_size, icon_size))

            spots: dict[tuple[int, int], list[tuple[float, float]]] = {}
            for d in self.sim.drones:
                if d.delivered:
                    continue
                pos = self.sim.get_drone_position(d.drone_id)
                if pos is None:
                    continue
                sx = ox + (pos[0] - min_x) * cw
                sy = oy + (pos[1] - min_y) * ch
                k = (round(sx), round(sy))
                spots.setdefault(k, []).append((sx, sy))

            for pts in spots.values():
                n = len(pts)
                for i, (sx, sy) in enumerate(pts):
                    if n > 1:
                        ang = 2 * math.pi * i / n
                        sx += math.cos(ang) * icon_size * 0.5
                        sy += math.sin(ang) * icon_size * 0.5
                    rect = icon.get_rect(center=(sx, sy))
                    screen.blit(icon, rect)

            done = sum(1 for d in self.sim.drones if d.delivered)
            hud = [
                f"Turn: {self.sim.turn}",
                f"Delivered: {done}/{len(self.sim.drones)}",
                f"Auto: {'ON' if auto else 'OFF'}  Speed: {1.0/interval:.1f}x",
                "ESC quit | SPACE step | P auto | +/- speed",
            ]
            y0 = 12
            for line in hud:
                txt = font.render(line, True, (40, 40, 40))
                screen.blit(txt, (12, y0))
                y0 += 20

            pygame.display.flip()

        pygame.quit()
