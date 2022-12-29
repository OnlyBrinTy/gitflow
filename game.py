from entities import AnotherThread, Player
from math import atan, degrees
from texture import Texture
from map import Map
import weapon
import pygame

BACKGROUND_COLOR = '#71ddee'
WIDTH, HEIGHT = 1280, 720
FPS = 120


class Camera(pygame.sprite.GroupSingle):
    offset = pygame.math.Vector2()

    def camera_centering(self):   # установка сдвига камеры так, чтобы игрок оказался по центру
        self.offset.x = self.sprite.rect.center[0] - WIDTH // 2
        self.offset.y = self.sprite.rect.center[1] - HEIGHT // 2

    def draw(self, groups, interface, screen):
        self.camera_centering()

        screen.fill(BACKGROUND_COLOR)   # заливка фона

        for group in groups:
            for sprite in group.sprites():
                screen.blit(sprite.image, sprite.blit_pos - self.offset)

        for texture in interface:  # каждая текстура выводится на экран друг за другом с учётом сдвига камеры
            screen.blit(texture.image, texture.blit_pos)

        pygame.display.update()


class Game:
    def __init__(self):
        pygame.init()

        self.screen = pygame.display.set_mode((WIDTH, HEIGHT), vsync=True)

        self.camera = Camera()  # через камеру происходит отображение всего на экране
        self.entities = pygame.sprite.Group()
        self.map = Map('test_level.txt')

        self.player = Player((WIDTH // 2, HEIGHT // 2), (self.camera, self.entities))
        self.interface = []
        # в interface лежат текстуры, которые будут затем выводится на экран
        # они лежат в порядке отображения. Сначала рисуем землю и поверх неё рисуем игрока

        self.thread = AnotherThread(self.camera)
        self.thread.start()

        weap = weapon.BulletAmount()

        clock = pygame.time.Clock()
        running = True

        while running:
            self.thread.update_groups.set()  # делаем запрос на обновление персонажа

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.display.quit()
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        self.screen.blit(weap.get_bullet(), (100, 100))
                elif event.type == pygame.MOUSEMOTION:
                    self.player.set_angle(self.check_angle(event.pos))

            while self.thread.update_groups.is_set():    # ждём пока персонаж не обработает своё положение
                pass

            self.camera.draw((self.map, self.entities), self.interface, self.screen)
            pygame.display.update()

            clock.tick(FPS)

    def check_angle(self, mouse_pos):   # определение угла поворота в зависимости от положение мыши
        quarters = {(True, False): 0, (False, False): 1, (False, True): 2, (True, True): 3}

        x_dist, y_dist = mouse_pos - pygame.Vector2(self.player.rect.center - self.camera.offset)
        quart_num = quarters[(x_dist > 0, y_dist > 0)]

        if x_dist == 0 or y_dist == 0:
            add_angle = 0

            if x_dist == 0:
                if y_dist > 0:
                    quart_num = 3
                else:
                    quart_num = 1
            else:
                if x_dist > 0:
                    quart_num = 0
                else:
                    quart_num = 2
        else:
            add_angle = degrees(atan(x_dist / y_dist))

            if quart_num in (0, 2):
                add_angle += 90

        return add_angle + 90 * quart_num
