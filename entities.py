from math import sin, cos, radians, atan, degrees
from random import randint, getrandbits
from shapely import LineString, Point
from threading import Thread, Event
from texture import Texture
from rectangle import Rect
from weapon import Weapon
from time import time
import numpy as np
import pygame


class Entity(pygame.sprite.Sprite, Texture):
    def __init__(self, start_pos, file_name, groups):
        pygame.sprite.Sprite.__init__(self, *groups)
        Texture.__init__(self, start_pos, pygame.image.load(file_name))

        self.vectors = Vectors()
        # Так как персонаж по умолчанию крутится очень странно,
        # чтобы скомпенсировать его странное вращение в нормальное используется отдельный вектор
        self.rect_correction = pygame.Vector2()
        # есть _original_image - это вид картинки по умолчанию(без наклона).
        # Нужна на случай, если картинка крутится
        self._original_image = self.image
        # вместо встроенного в pygame rect я использую свой аналог.
        self.finite_angle = self.angle = 0
        # угол наклона картинки
        # Он отличается тем, что он поддерживает дробные числа в координатах.
        self.add_rect = Rect(self.rect)
        self.mask = pygame.mask.from_surface(self.image)

    def set_angle(self, slowdown):
        diff = self.finite_angle - self.angle

        diff = min(diff, (360 - abs(diff)) * (1 - int(diff > 0) * 2), key=abs)
        if abs(diff) < 1.5 * slowdown:
            self.angle = self.finite_angle
        else:
            adjust = (20 / (1 + 1.2 ** -(abs(diff) - 20))) * slowdown * (1 - int(diff < 0) * 2)

            self.angle = (self.angle + adjust) % 360

        self.image = pygame.transform.rotate(self._original_image, self.angle + 1)  # поворот картинки
        self.mask = pygame.mask.from_surface(self.image)  # меняем маску
        self.rect.size = self.image.get_size()  # меняем rect.size на новый

        img_half_w = self.image.get_width() / 2
        img_half_h = self.image.get_height() / 2

        self.rect_correction.update(self.add_rect.h_width - img_half_w, self.add_rect.h_height - img_half_h)
        self.rect.topleft = self.add_rect.topleft + self.rect_correction  # устанавливаем правильный  topleft

    def get_wall_collision(self, walls_group, check_collision=False):
        side = walls_group.cell_size
        x_ps = y_ps = np.empty(0, dtype=np.int8)
        positive_x = positive_y = None
        for wall in pygame.sprite.spritecollide(self, walls_group, False):
            if wall.kind and pygame.sprite.collide_mask(self, wall):  # если столкнулись с красным блоком
                if check_collision:
                    return True

                offset = pygame.Vector2(self.rect.topleft) - wall.rect.topleft
                collide_mask = wall.mask.overlap_mask(self.mask, offset)

                bit_array = np.ones(collide_mask.get_size(), dtype=np.bool_)
                cords = np.where(bit_array)
                bit_array[cords] = np.array(list(map(collide_mask.get_at, np.array(cords).T)), dtype=np.bool_)

                y_penetration = x_penetration = 0
                y_wall = any(wall.bounds[:2])

                if y_wall:
                    if positive_y is None and wall.bounds[0] != wall.bounds[1]:
                        positive_y = wall.bounds[0]

                    axis_array = np.where(np.any(bit_array, axis=0))

                    axis_max = np.max(axis_array)
                    axis_min = np.min(axis_array)

                    if positive_y is None:
                        if np.all(axis_array):
                            positive_y = self.rect.centery < wall.rect.centery
                        else:
                            y_penetration = np.min(axis_max, axis_min)

                            positive_y = y_penetration > 0

                    if positive_y == False and axis_max == 49:
                        y_penetration = axis_min - side
                    elif positive_y == True and axis_min == 0:
                        y_penetration = axis_max + 1

                y_ps = np.append(y_ps, y_penetration)

                if any(wall.bounds[2:]):
                    if positive_x is None and wall.bounds[2] != wall.bounds[3]:
                        positive_x = wall.bounds[2]

                    axis_array = np.where(np.any(bit_array, axis=1))

                    axis_max = np.max(axis_array)
                    axis_min = np.min(axis_array)

                    if positive_x is None:
                        if np.all(axis_array):
                            positive_x = self.rect.centerx < wall.rect.centerx
                        else:
                            x_penetration = np.min(axis_max, axis_min)

                            positive_x = x_penetration > 0

                    if positive_x == False and axis_max == 49:
                        x_penetration = axis_min - side
                    elif positive_x == True and axis_min == 0:
                        x_penetration = axis_max + 1

                x_ps = np.append(x_ps, x_penetration)

                if y_ps[-1] and x_ps[-1] and abs(y_ps[-1] - x_ps[-1]) > 3:
                    abs_x, abs_y = abs(x_ps[-1]), abs(y_ps[-1])
                    if abs_x > abs_y:
                        x_ps[-1] = 0
                    elif abs_y > abs_x:
                        y_ps[-1] = 0
                elif positive_y is not None:
                    if y_wall and positive_y != (self.rect.centery < wall.rect.centery):
                        y_ps[-1] = 0
                    elif positive_x != (self.rect.centerx < wall.rect.centerx):
                        x_ps[-1] = 0

        if np.any(x_ps) or np.any(y_ps):
            return [max(x_ps, key=abs), max(y_ps, key=abs)]

    def check_entity_collision(self):
        for entity in self.groups()[0]:
            if self is not entity and entity.__class__.__name__ != 'Bullet' and pygame.sprite.collide_mask(self, entity):  # если столкнулись с кем-то или с пулей
                return entity

    def basic_entity_update(self, delay):
        slowdown = delay / 0.035  # отклонение от стандартного течения времени (1 кадр в 0.035 секунды)

        self.motion(slowdown)  # обрабатываем физику и нажатия (если есть)
        self.set_angle(slowdown)  # теперь у кручения тоже есть своя физика


class Actor:
    animation_progress = 0
    to_shoot = False

    def shoot(self):
        if self.weapon.shoot():
            pos_in_radians = radians(self.angle + 87)
            dir_in_radians = radians(self.angle + 90)

            hypotinuse = self.add_rect.h_width + 15

            barrel_addition = hypotinuse * sin(pos_in_radians), hypotinuse * cos(pos_in_radians)
            bullet_pos = pygame.Vector2(self.add_rect.center) + barrel_addition

            direction = self.add_rect.h_width * sin(dir_in_radians), self.add_rect.h_width * cos(dir_in_radians)

            Bullet(bullet_pos, 'assets/bullet.png', (self.groups()[0],), direction, self.angle)

            self.to_shoot = False

    def start_damage_animation(self):
        self.animation_progress = 20

    def damage_animation(self):
        if self.animation_progress and False:
            self._original_image = pygame.image.load(f'assets/damage_animation/{self.animation_progress}.png')
            self.animation_progress -= 1

    def get_adjust(self, slowdown):
        def formula(speed, depth):
            curr_increase = 2 / 1.15 ** speed

            if depth:
                return curr_increase + formula(speed + curr_increase, depth - 1)

            return curr_increase * (slowdown % 1)

        return formula(sum(self.vectors.velocity), int(slowdown))

    def limit_speed(self, overload):
        self.vectors.velocity -= self.vectors.velocity / sum(self.vectors.velocity) * overload

    def basic_actor_update(self, group):
        collide_entity = self.check_entity_collision()

        if collide_entity:
            bottom_right = map(lambda c: c[0] > c[1], zip(self.add_rect.center, collide_entity.add_rect.center))
            self.add_rect.topleft += tuple(map(lambda n: int(n) * 12 - 6, bottom_right))
            self.rect.topleft = self.add_rect.topleft + self.rect_correction

        wall_entrance = self.get_wall_collision(group)  # на сколько пикселей вошёл в стену

        if wall_entrance:
            self.add_rect.x -= wall_entrance[0]  # пробуем вытолкнуться по оси x
            self.rect.topleft = self.add_rect.topleft + self.rect_correction

            if self.get_wall_collision(group, check_collision=True) :  # если мы до сих пор в стене
                self.add_rect.y -= wall_entrance[1]  # пробуем вытолкнуться по оси y
                self.rect.topleft = self.add_rect.topleft + self.rect_correction

        if self.to_shoot:
            self.shoot()

        if self.hp <= 0:
            self.kill()

        self.damage_animation()

        if wall_entrance:
            return pygame.Vector2(wall_entrance)


class Player(Entity, Actor):  # Это спрайт для групп camera и entities
    def __init__(self, start_pos, bullets, hp, file_name, groups):
        Entity.__init__(self, start_pos, file_name, groups)

        self.max_speed = 10
        self.weapon = Weapon(bullets)
        self.hp = hp

    def motion(self, slowdown):
        keys = pygame.key.get_pressed()
        w, a, s, d = keys[pygame.K_w], keys[pygame.K_a], keys[pygame.K_s], keys[pygame.K_d]
        boost = self.get_adjust(slowdown)

        self.vectors.direction += boost * (bool(d) - bool(a)), boost * (bool(s) - bool(w))

        if w == s and a == d and self.vectors.velocity:
            fractions = pygame.Vector2(self.vectors.velocity / sum(self.vectors.velocity))

            self.vectors.velocity -= tuple(map(min, zip(self.vectors.velocity, fractions * boost)))
        elif w == s:
            self.vectors.velocity -= 0, min(self.vectors.velocity.y, boost)
        elif a == d:
            self.vectors.velocity -= min(self.vectors.velocity.x, boost), 0

        if sum(self.vectors.velocity) > self.max_speed:
            overload = sum(self.vectors.velocity) - self.max_speed

            if w != s and a != d:
                self.limit_speed(overload)
            else:
                self.vectors.velocity -= overload * bool(w == s), overload * bool(a == d)

        # для компенсации слишком редкого/частого обновления персонажа
        # скорость умножается на коэффициент замедления времени
        #   add_rect отображает положение игрока в пространстве без учёта кручения в дробных числах и не меняет размер
        self.add_rect.topleft += self.vectors.direction * slowdown
        #   обычный rect нужен для отображения картинки, его размеры зависят от разворота картинки,
        #   а topleft всегда изменяется в зависимости от разворота картинки (чтобы не болтало, как это было раньше)
        self.rect.topleft = self.add_rect.topleft + self.rect_correction

    def update(self, delay, group):
        self.basic_entity_update(delay)
        self.basic_actor_update(group)


class Enemy(Entity, Actor):
    def __init__(self, start_pos, bullets, hp, file_name, groups):
        Entity.__init__(self, start_pos, file_name, groups)

        self.wanted_way = pygame.Vector2()
        self.stuck_timer = self.waiting_timer = 0
        self.previous_pos = pygame.Vector2(self.rect.center)
        self.see_player = False
        self.target_point = None, None

        self.max_speed = 10
        self.hp = hp
        self.weapon = Weapon(bullets)

    def motion(self, slowdown):
        boost = self.get_adjust(slowdown)

        self.vectors.direction += self.wanted_way * boost

        if not self.wanted_way and self.vectors.direction:
            fractions = pygame.Vector2(self.vectors.velocity / sum(self.vectors.velocity))

            self.vectors.velocity -= tuple(map(min, zip(self.vectors.velocity, fractions * boost)))
        else:
            overload = sum(self.vectors.velocity) - self.max_speed
            if overload > 0:
                self.limit_speed(overload)

        self.add_rect.topleft += self.vectors.direction * slowdown
        self.rect.topleft = self.add_rect.topleft + self.rect_correction

    def check_the_point(self, wall_shape, point):
        view_line = LineString((self.add_rect.center, point))

        self.see_player = not view_line.intersects(wall_shape)
        if self.see_player:
            self.target_point = point

    def go_to_point(self, point):
        dist = pygame.Vector2(point) - self.add_rect.center
        total_dist = sum(set(map(abs, dist)))

        if total_dist > 100:
            self.wanted_way = dist / total_dist
        elif point == self.target_point:
            self.wanted_way.update(0, 0)
            self.target_point = None, None

    def find_random_route(self, wall_shape):
        def random_margin():
            return randint(100, 300) * (getrandbits(1) * 2 - 1)

        while True:
            rand_point = self.rect.center + pygame.Vector2(random_margin(), random_margin())
            if not wall_shape.contains(Point(rand_point)):
                self.current_target = self.target_point = rand_point
                break

        if not self.waiting_timer:
            self.waiting_timer = randint(1, 21)

    def routing(self, delay):
        if any(self.target_point):
            if not self.stuck_timer:
                total_difference = sum(set(map(abs, self.rect.center - self.previous_pos)))
                if total_difference < 70 * self.max_speed * delay and self.last_knockout:
                    self.current_target -= self.last_knockout * 3
                else:
                    self.current_target = self.target_point

                self.stuck_timer = 5
                self.previous_pos.update(self.rect.center)

            self.go_to_point(self.current_target)
            self.stuck_timer -= 1

    def rotate_to_path(self):
        if not self.see_player and self.wanted_way:
            add_angle = degrees(atan(self.wanted_way[0] / self.wanted_way[1]))
            if add_angle < 0:
                add_angle += 90

            x, y = tuple(map(lambda c: int(c > 0), self.wanted_way))
            self.finite_angle = 180 * y + 90 * (1 - y - x + 2 * x * y) + add_angle

    def update(self, delay, group):
        self.basic_entity_update(delay)
        self.last_knockout = self.basic_actor_update(group)

        if self.waiting_timer:
            self.wanted_way.update(0, 0)
        else:
            self.rotate_to_path()
            self.routing(delay)

        self.waiting_timer = max(0, self.waiting_timer - 1)


class Bullet(Entity):
    def __init__(self, start_pos, file_name, groups, direction, angle):
        Entity.__init__(self, start_pos, file_name, groups)

        self.vectors.direction.update(direction)
        self.vectors.direction /= 10

        self.finite_angle, self.angle = angle, angle + 1
        self.damage = 1
        self.set_angle(1)

    def motion(self, slowdown):
        self.add_rect.topleft += self.vectors.direction * slowdown
        self.rect.topleft = self.add_rect.topleft + self.rect_correction

    def update(self, delay, group):
        self.basic_entity_update(delay)

        if self.get_wall_collision(group, check_collision=True):
            self.kill()
        else:
            shot_actor = self.check_entity_collision()

            if shot_actor:
                shot_actor.hp -= self.damage
                shot_actor.start_damage_animation()

                self.kill()


class EntityThread(Thread):  # обработка сущностей вынесена в отдельный поток
    def __init__(self, walls_group, *groups_to_update):
        super().__init__()

        self.groups_to_update = groups_to_update  # группы, которые будем обновлять (возможно не только entities)
        self.collide_group = walls_group  # група со спрайтами, с которыми будет происходить столкновение

        self.update_groups = Event()  # флажок означающий, что надо обновить группы
        self.terminated = Event()  # флажок означающий, жив или мёртв этот поток (так можно убить извне)

    def run(self):
        start = time()

        while not self.terminated.is_set():
            if self.update_groups.is_set():
                delay = time() - start  # считаем задержку между запросами на обновление
                start = time()

                for group in self.groups_to_update:
                    group.update(delay, self.collide_group)

                self.update_groups.clear()  # ставим флажок обновления на False


class Vectors:  # содержит direction (пример [5.5, -4.5]) и его аналог velocity, но под модулем (пример [5.5, 4.5])
    def __init__(self, direction=()):
        self.direction = pygame.Vector2(*direction)

    @property
    def velocity(self):
        return pygame.Vector2(*map(abs, self.direction))

    @velocity.setter
    def velocity(self, value):
        direction_mask = pygame.Vector2(*map(lambda x: bool(x >= 0) * 2 - 1, self.direction))

        self.direction = direction_mask.elementwise() * value
