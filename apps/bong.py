import time
from typing import List
from pygame.event import Event
from pymunk.vec2d import Vec2d
from lib.bicturemaker import Bicturemaker
import pymunk
from lib.barser import BarserMethod
from lib.bolygonbetector import BolygonBetector
import pygame
from lib.bame import Bame, BarsedContext, LoadContext, TickContext
import random
import pygame.gfxdraw
import pymunk.autogeometry


bols = BolygonBetector()


def barse_red_bolygons(image, field):
    field["bolygons"] = bols.detect(image)


class Bong:

    barse_red_lines = BarserMethod(barse_red_bolygons)
    
    def load(self, context: LoadContext) -> None:
        self.bicturemaker = context.bicturemaker
        self.bicturemaker.set_origin(Bicturemaker.CENTER)
        self.bicturemaker.set_scale(1/20)

        self.space = pymunk.Space()

        self.__init_objects()

        self.__reset()

        self.left_up = False
        self.left_down = False
        self.right_up = False
        self.right_down = False

        self.drawn_lines = None
        self.last_updated = None

    def __init_objects(self):
        self.border_y = 5
        self.top = pymunk.Segment(self.space.static_body, (-10, self.border_y), (10, self.border_y), 0)
        self.top.friction = 0
        self.top.elasticity = 1
        self.bottom = pymunk.Segment(self.space.static_body, (-10, -self.border_y), (10, -self.border_y), 0)
        self.bottom.friction = 0
        self.bottom.elasticity = 1
        self.space.add(self.top)
        self.space.add(self.bottom)

        ball_mass = 1
        self.ball_radius = 0.5
        ball_moment = pymunk.moment_for_circle(ball_mass, 0, self.ball_radius)
        self.ball = pymunk.Body(ball_mass, ball_moment)
        self.ball_position_init = Vec2d(0, 0)
        self.ball.position = self.ball_position_init
        ball_shape = pymunk.Circle(self.ball, self.ball_radius)
        ball_shape.friction = 0.3
        ball_shape.elasticity = 1
        self.space.add(self.ball, ball_shape)

        left_box_mass = 1
        self.left_box_size = Vec2d(1, 2)
        left_box_moment = pymunk.moment_for_box(left_box_mass, self.left_box_size)
        self.left_box = pymunk.Body(left_box_mass, left_box_moment)
        self.left_box.body_type = pymunk.Body.KINEMATIC
        self.left_box_position_init = Vec2d(-9.5, 0)
        self.left_box.position = self.left_box_position_init
        self.left_box_radius = 0.1
        left_box_true_size = self.left_box_size - (self.left_box_radius, self.left_box_radius)
        left_box_shape = pymunk.Poly.create_box(self.left_box, left_box_true_size, self.left_box_radius)
        left_box_shape.friction = 0.3
        left_box_shape.elasticity = 1
        self.space.add(self.left_box, left_box_shape)

        right_box_mass = 1
        self.right_box_size = Vec2d(1, 2)
        right_box_moment = pymunk.moment_for_box(right_box_mass, self.right_box_size)
        self.right_box = pymunk.Body(right_box_mass, right_box_moment)
        self.right_box.body_type = pymunk.Body.KINEMATIC
        self.right_box_position_init = Vec2d(9.5, 0)
        self.right_box.position = self.right_box_position_init
        self.right_box_radius = 0.1
        right_box_true_size = self.right_box_size - (self.right_box_radius, self.right_box_radius)
        right_box_shape = pymunk.Poly.create_box(self.right_box, right_box_true_size, self.right_box_radius)
        right_box_shape.friction = 0.3
        right_box_shape.elasticity = 1
        self.space.add(self.right_box, right_box_shape)

        self.ball_velocity_init = 5

    def tick(self, context: TickContext, barsed_context: BarsedContext):

        if self.__handle_events(context.events):
            return True

        self.__handle_barsed_context(barsed_context)

        self.__handle_physics()

        self.space.step(context.delta_ms / 1000)

        #print(self.ball.velocity)

        self.__render()

    def __reset(self):
        self.ball.position = self.ball_position_init
        starting_direction = 1 if bool(random.getrandbits(1)) else -1
        self.ball.velocity = (self.ball_velocity_init * starting_direction, 0)

        self.left_box.position = self.left_box_position_init
        self.right_box.position = self.right_box_position_init

    def __handle_events(self, events: List[Event]):
        for event in events:
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    return True
                if event.key == pygame.K_w:
                    self.left_up = True
                if event.key == pygame.K_s:
                    self.left_down = True
                if event.key == pygame.K_UP:
                    self.right_up = True
                if event.key == pygame.K_DOWN:
                    self.right_down = True
                if event.key == pygame.K_r:
                    self.__reset()
            if event.type == pygame.KEYUP:
                if event.key == pygame.K_w:
                    self.left_up = False
                if event.key == pygame.K_s:
                    self.left_down = False
                if event.key == pygame.K_UP:
                    self.right_up = False
                if event.key == pygame.K_DOWN:
                    self.right_down = False
        return False

    def __handle_barsed_context(self, barsed_context: BarsedContext):
        t = time.time()

        if self.last_updated is None or t - self.last_updated > 1:
            self.last_updated = t

            drawn_lines = barsed_context.data["bolygons"]
            if drawn_lines is not None:
                if self.drawn_lines:
                    self.space.remove(*self.drawn_lines)
                self.drawn_lines = []
                for line in drawn_lines:
                    for convexed_line in pymunk.autogeometry.convex_decomposition(line, 10):
                        if len(convexed_line) < 4:
                            continue
                        parsed_line = []
                        for point in convexed_line:
                            parsed_line.append(self.bicturemaker.game2munk(point))
                        line_ground = pymunk.Poly(self.space.static_body, parsed_line)
                        line_ground.friction = 1
                        self.space.add(line_ground)
                        self.drawn_lines.append(line_ground)

    def __handle_physics(self):
        if self.left_up and not self.left_down and self.left_box.position.y < (self.border_y - self.left_box_size.y / 2):
            self.left_box.velocity = (0, 2)
        elif self.left_down and not self.left_up and self.left_box.position.y > -(self.border_y - self.left_box_size.y / 2):
            self.left_box.velocity = (0, -2)
        else:
            self.left_box.velocity = (0, 0)
        if self.right_up and not self.right_down and self.right_box.position.y < (self.border_y - self.right_box_size.y / 2):
            self.right_box.velocity = (0, 2)
        elif self.right_down and not self.right_up and self.right_box.position.y > -(self.border_y - self.right_box_size.y / 2):
            self.right_box.velocity = (0, -2)
        else:
            self.right_box.velocity = (0, 0)

    def __render(self):
        self.bicturemaker.draw_line((255, 255, 0), self.top.a, self.top.b)
        self.bicturemaker.draw_line((255, 255, 0), self.bottom.a, self.bottom.b)
        self.bicturemaker.draw_aacircle(self.ball.position, self.ball_radius, (255, 0, 0))
        left_box_topleft = (self.left_box.position[0] - self.left_box_size[0] / 2, self.left_box.position[1] + self.left_box_size[1] / 2)
        left_box_bottomright = (left_box_topleft[0] + self.left_box_size[0], left_box_topleft[1] - self.left_box_size[1])
        self.bicturemaker.draw_rect((255, 255, 0), left_box_topleft, left_box_bottomright, border_radius=self.left_box_radius)
        right_box_topleft = (self.right_box.position[0] - self.right_box_size[0] / 2, self.right_box.position[1] + self.right_box_size[1] / 2)
        right_box_bottomright = (right_box_topleft[0] + self.right_box_size[0], right_box_topleft[1] - self.right_box_size[1])
        self.bicturemaker.draw_rect((255, 255, 0), right_box_topleft, right_box_bottomright, border_radius=self.right_box_radius)

        for line in self.drawn_lines:
            self.bicturemaker.draw_polygon((63, 0, 0), line)


if __name__ == '__main__':
    Bame(Bong).run()
