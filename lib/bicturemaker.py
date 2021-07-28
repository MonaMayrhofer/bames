from typing import Tuple
import numpy as np

import pygame
import pygame.gfxdraw
import pygame.draw


class Bicturemaker:

    TOP_LEFT = (0, 0)
    TOP_CENTER = (0.5, 0)
    TOP_RIGHT = (1, 0)
    CENTER_LEFT = (0, 0.5)
    CENTER = (0.5, 0.5)
    CENTER_RIGHT = (1, 0.5)
    BOTTOM_LEFT = (0, 1)
    BOTTOM_CENTER = (0.5, 1)
    BOTTOM_RIGHT = (1, 1)

    resolution: Tuple[int, int]
    origin: Tuple[int, int]
    scale: int

    def __init__(self, screen, barameters):
        self.screen = screen
        self.resolution = screen.get_size()


    def draw_sprite(self, sprite, position, offset=(0, 0), rotation=0):
        angle = np.degrees(np.arctan2(rotation.y, rotation.x))
        actual_position = (position[0] + offset[0], position[1] + offset[1])
        self.screen.blit(pygame.transform.rotate(sprite, angle), self.munk2game(actual_position))

    def draw_line(self, color, start_pos, end_pos, width=1):
        pygame.draw.line(self.screen, color, self.munk2game(start_pos), self.munk2game(end_pos), width)

    def draw_aacircle(self, position, radius, color):
        actual_position = self.munk2game(position)
        pygame.gfxdraw.aacircle(self.screen, actual_position[0], actual_position[1], radius * self.scale, color)

    def draw_rect(self, color, rect, width=0, border_radius=-1):
        topleft = self.munk2game(rect.topleft)
        bottomright = self.munk2game(rect.bottomright)
        width_height = (bottomright[0] - topleft[0], topleft[1] - bottomright[1])
        rect = pygame.Rect(topleft, width_height)
        pygame.draw.rect(self.screen, color, rect, width, border_radius)

    def draw_lines(self, color, closed, points, width=1):
        pygame_points = []
        for point in points:
            pygame_points.append(self.munk2game(point))
        pygame.draw.lines(self.screen, color, closed, pygame_points, width)

    def draw_polygon(self, color, polygon):
        pygame_vertices = []
        for vertex in polygon.get_vertices():
            pygame_vertices.append(self.munk2game(vertex))
        pygame.draw.polygon(self.screen, color, pygame_vertices)


    def set_origin(self, origin: Tuple[int, int]):
        self.origin = (origin[0] * self.resolution[0], origin[1] * self.resolution[1])

    def set_scale(self, scale: int):
        self.scale = scale * self.screen.get_width()

    def munk2game(self, point):
        return (self.origin[0] + point[0] * self.scale, self.origin[1] - point[1] * self.scale)

    def game2munk(self, point):
        return ((point[0] - self.origin[0]) / self.scale, (self.origin[1] - point[1]) / self.scale)
