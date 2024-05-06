from window_elements import Button, Label
import pygame

if __name__ == '__main__':
    from game import Game
    from time import time
    from os import stat

FIRST_LEVEL = 1
GAME_NAME = 'Hotline Fortress'
EXTRA_WIDTH, EXTRA_HEIGHT = 600, 400    # размеры для окон интерфейса
BACKGROUND_COLOR = (41, 52, 80)


class ExtraWindow:  # общий класс для всех окон интерфейса
    button_image = pygame.image.load('assets/button.png')

    def __init__(self, buttons=(), labels=()):
        pygame.init()

        pygame.display.set_caption(GAME_NAME)

        self.screen = pygame.display.set_mode((EXTRA_WIDTH, EXTRA_HEIGHT))

        self.labels = labels
        self.buttons = buttons
        self.running = True

        while self.running:
            self.draw()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                    pygame.display.quit()
                elif event.type == pygame.MOUSEBUTTONDOWN:
                    if event.button == 1:
                        for button in self.buttons:
                            if button.rect.collidepoint(event.pos):  # если мышка над кнопкой
                                self.action(button())   # делаем что-то в action

    def draw(self):
        self.screen.fill(BACKGROUND_COLOR)

        for button in self.buttons:
            button.draw(self.screen)

        for label in self.labels:
            label.draw(self.screen)

        pygame.display.update()


class SettingsWindow(ExtraWindow):
    def __init__(self):
        img_rect = self.button_image.get_rect()  # Размеры картинки
        image_amount = 3  # Количество картинок на экране
        center_x = (EXTRA_WIDTH - img_rect.width) // 2  # координата х для центрального расположения
        center_y = (EXTRA_HEIGHT - img_rect.height * image_amount) // (image_amount + 1)

        # кнопки для окна
        easy_button = Button((center_x, center_y), self.button_image, 'easy')
        medium_button = Button((center_x, center_y * 2 + img_rect.height), self.button_image, 'medium')
        hard_button = Button((center_x, center_y * 3 + img_rect.height * 2), self.button_image, 'hard')

        super().__init__((easy_button, medium_button, hard_button))

    def action(self, button_text):
        pygame.display.quit()

        difficulty = {'easy': 1, 'medium': 2, 'hard': 3}[button_text]

        with open("progress/progress.txt", 'r+') as file:
            file.truncate(0)

        game_start_time = time()  # запускем таймер в начале. Отображает время игровой сессии
        EndWindow(*Game().start(True, difficulty, FIRST_LEVEL), game_start_time)
        self.running = False


class StartWindow(ExtraWindow):
    def __init__(self):
        img_rect = self.button_image.get_rect()  # Размеры картинки
        image_amount = 2  # Количество картинок на экране
        center_x = (EXTRA_WIDTH - img_rect.width) // 2  # координата х для центрального расположения
        center_y = (EXTRA_HEIGHT - img_rect.height * image_amount) // (image_amount + 1)

        start_button = Button((center_x, center_y + 60), self.button_image, 'start')
        continue_button = Button((center_x, center_y * 2 + 40 + img_rect.height), self.button_image, 'continue')
        game_name = Label((EXTRA_WIDTH // 2, 70), GAME_NAME, 70)
        hint_label = Label((500, 320), '', 20)

        super().__init__((start_button, continue_button), (game_name, hint_label))

    def action(self, button_text):
        if button_text == 'start':  # Обработка нажатия на кнопку start
            self.running = False
            pygame.display.quit()

            RulesWindow()   # запуск окна с правилами
        # Обработка нажатия на кнопку continue
        elif button_text == 'continue':
            if stat("progress/progress.txt").st_size:   # если файл с прогрессом не пустой
                self.running = False
                pygame.display.quit()

                game_start_time = time()  # запускем таймер в начале. Отображает время игровой сессии
                # Game при завершении вернёт итоговую надпись и счёт
                EndWindow(*Game().start(False), game_start_time)
            else:
                self.labels[1].change_text('* You have no saves yet')


class RulesWindow(ExtraWindow):
    def __init__(self):
        center_x = (EXTRA_WIDTH - self.button_image.get_width()) // 2

        start_button = Button((center_x, 260), self.button_image, ' ok ')
        rules_1 = Label((EXTRA_WIDTH // 2, 60), 'Your goal is to get into the dungeon', 30)
        rules_2 = Label((EXTRA_WIDTH // 2, 90), 'and clear it of enemies. After killing', 30)
        rules_3 = Label((EXTRA_WIDTH // 2, 120), 'all the enemies on the level, you pass to', 30)
        rules_4 = Label((EXTRA_WIDTH // 2, 150), 'the next level. The control is carried out', 30)
        rules_5 = Label((EXTRA_WIDTH // 2, 180), 'on the WASD keys. To shoot, point the sight', 30)
        rules_6 = Label((EXTRA_WIDTH // 2, 210), 'at the enemy and click on the left mouse button', 30)

        super().__init__((start_button,), (rules_1, rules_2, rules_3, rules_4, rules_5, rules_6))

    def action(self, button_text):
        if button_text == ' ok ':
            self.running = False
            SettingsWindow()


class EndWindow(ExtraWindow):
    def __init__(self, summary, total_score, game_start_time):
        summary_label = Label((EXTRA_WIDTH // 2, 100), summary, 70)
        time_label = Label((EXTRA_WIDTH // 2, 250), f'Time: {int(time() - game_start_time)} sec', 35)
        score_label = Label((EXTRA_WIDTH // 2, 325), f'Score: {total_score}', 35)

        super().__init__((), (summary_label, time_label, score_label))


class PauseWindow(ExtraWindow):
    def __init__(self, game_class):
        self.game = game_class

        center_x = (EXTRA_WIDTH - self.button_image.get_width()) // 2

        save_button = Button((center_x, 150), self.button_image, 'save')
        leave_game_button = Button((center_x, 285), self.button_image, 'exit game')
        pause_label = Label((EXTRA_WIDTH // 2, 75), 'Pause', 70)
        saves_left_label = Label((EXTRA_WIDTH // 2, 265), f'You have {self.game.saves_left} saves left', 20)

        super().__init__((save_button, leave_game_button), (pause_label, saves_left_label))

    def action(self, button_text):
        if button_text == 'save':
            self.game.save_game()   # сохраняем прогресс
            # изменяем табличку с оставшимися сохранениями
            self.labels[1].change_text(f'You have {self.game.saves_left} saves left')
        elif button_text == 'exit game':
            exit()


if __name__ == '__main__':
    StartWindow()   # запуск главного меню
