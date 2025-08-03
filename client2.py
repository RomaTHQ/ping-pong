from pygame import *
import socket
import json
from threading import Thread
import os
import sys

# ---PYGAME НАЛАШТУВАННЯ ---
WIDTH, HEIGHT = 800, 600
init()
mixer.init()
screen = display.set_mode((WIDTH, HEIGHT))
clock = time.Clock()
display.set_caption("Пінг-Понг")

# --- ШРИФТИ ---
font_title = font.Font(None, 64)
font_button = font.Font(None, 36)
font_win = font.Font(None, 72)
font_main = font.Font(None, 36)
font_small = font.Font(None, 24)


# === ЗАВАНТАЖЕННЯ ЗВУКІВ ===
def load_sound_safe(path, volume=0.5):
    """
    Безпечно завантажує звук з обробкою помилок
    path - шлях до файлу
    volume - гучність від 0.0 до 1.0
    Повертає звук або None при помилці
    """
    try:
        sound = mixer.Sound(path)
        sound.set_volume(volume)
        return sound
    except Exception as e:
        print(f"⚠️ Не вдалося завантажити звук {path}: {e}")
        return None


def load_music_safe(path, volume=0.3):
    """
    Безпечно завантажує фонову музику
    path - шлях до файлу
    volume - гучність від 0.0 до 1.0
    """
    try:
        mixer.music.load(path)
        mixer.music.set_volume(volume)
        return True
    except Exception as e:
        print(f"⚠️ Не вдалося завантажити фонову музику {path}: {e}")
        return False


print("🔊 Завантажую звуки...")
# Завантаження звукових ефектів
paddle_hit_sound = load_sound_safe('audio/paddle_hit.wav', 0.6)  # Звук удару по ракетці
wall_hit_sound = load_sound_safe('audio/wall_hit.wav', 0.4)      # Звук удару об стіну
menu_click_sound = load_sound_safe('audio/menu_click.wav', 0.5)   # Звук кліку в меню
win_sound = load_sound_safe('audio/win.wav', 0.7)                # Звук перемоги
lose_sound = load_sound_safe('audio/lose.wav', 0.7)              # Звук поразки
background_music_loaded = load_music_safe('audio/background_music.mp3', 0.3)

# Змінна для відстеження стану фонової музики
music_playing = False


# === ЗАВАНТАЖЕННЯ ЗОБРАЖЕНЬ ===
def load_image_safe(path, size=None):
    """
    Безпечно завантажує зображення з обробкою помилок
    path - шлях до файлу
    size - розмір (width, height) або None
    Повертає зображення або None при помилці
    """
    try:
        img = image.load(path)
        if size:
            img = transform.scale(img, size)
        return img.convert_alpha()
    except:
        print(f"⚠️ Не вдалося завантажити {path}")
        return None


print("🎨 Завантажую зображення...")

# Фони
menu_bg = load_image_safe('images/backgrounds/menu_bg.jpg', (WIDTH, HEIGHT))
game_bg = load_image_safe('images/backgrounds/game_bg.jpg', (WIDTH, HEIGHT))
settings_bg = load_image_safe('images/backgrounds/settings_bg.jpg', (WIDTH, HEIGHT))
win_bg = load_image_safe('images/backgrounds/win_bg.jpg', (WIDTH, HEIGHT))

# Резервний фон
if game_bg is None:
    try:
        game_bg = image.load('bg.jpg')
        game_bg = transform.scale(game_bg, (WIDTH, HEIGHT))
    except:
        print("⚠️ Фонове зображення не знайдено")
        game_bg = None

# Ігрові елементи
ball_img = load_image_safe('images/game_elements/ball.png', (20, 20))
paddle1_img = load_image_safe('images/game_elements/paddle1.png', (20, 100))
paddle2_img = load_image_safe('images/game_elements/paddle2.png', (20, 100))

print("✅ Завантаження зображень завершено!")


# === ФУНКЦІЇ ДЛЯ РОБОТИ З МУЗИКОЮ ===
def start_background_music():
    """Запускає фонову музику"""
    global music_playing
    if background_music_loaded and game_settings["sound_enabled"] and not music_playing:
        try:
            mixer.music.play(-1)  # -1 означає нескінченне повторення
            music_playing = True
            print("🎵 Фонова музика запущена")
        except Exception as e:
            print(f"⚠️ Помилка запуску фонової музики: {e}")


def stop_background_music():
    """Зупиняє фонову музику"""
    global music_playing
    if music_playing:
        mixer.music.stop()
        music_playing = False
        print("🎵 Фонова музика зупинена")


def play_sound_effect(sound):
    """Програє звуковий ефект якщо звук увімкнено"""
    if sound and game_settings["sound_enabled"]:
        try:
            sound.play()
        except Exception as e:
            print(f"⚠️ Помилка відтворення звуку: {e}")


# === КЛАСИ ДЛЯ МЕНЮ ===
class Button:
    def __init__(self, x, y, width, height, text, action=None):
        self.rect = Rect(x, y, width, height)
        self.text = text
        self.action = action
        self.hovered = False

    def draw(self, screen):
        # Колір кнопки залежно від стану
        if self.hovered:
            color = (70, 130, 180)  # Світло-синій при наведенні
            text_color = (255, 255, 255)
        else:
            color = (50, 50, 100)  # Темно-синій звичайний стан
            text_color = (200, 200, 200)

        # Малюємо кнопку
        draw.rect(screen, color, self.rect)
        draw.rect(screen, (255, 255, 255), self.rect, 2)  # Біла рамка

        # Малюємо текст
        text_surface = font_button.render(self.text, True, text_color)
        text_rect = text_surface.get_rect(center=self.rect.center)
        screen.blit(text_surface, text_rect)

    def handle_event(self, event):
        if event.type == MOUSEMOTION:
            self.hovered = self.rect.collidepoint(event.pos)
        elif event.type == MOUSEBUTTONDOWN:
            if self.rect.collidepoint(event.pos) and self.action:
                play_sound_effect(menu_click_sound)
                self.action()
                return True
        return False


# === СТАНИ ГРИ ===
MENU = "menu"
SETTINGS = "settings"
CONNECTING = "connecting"
PLAYING = "playing"

current_state = MENU

# === НАЛАШТУВАННЯ ГРИ ===
game_settings = {
    "server_ip": "localhost",
    "server_port": 8080,
    "player_name": "Гравець",
    "sound_enabled": True
}


# === ФУНКЦІЇ ДЛЯ КНОПОК МЕНЮ ===
def start_game():
    global current_state
    current_state = CONNECTING
    start_background_music()
    print("🎮 Підключення до гри...")


def open_settings():
    global current_state
    current_state = SETTINGS
    print("⚙️ Відкриваю налаштування...")


def exit_game():
    print("👋 До побачення!")
    stop_background_music()
    quit()
    sys.exit()


def back_to_menu():
    global current_state
    current_state = MENU
    stop_background_music()
    print("🏠 Повертаюся до меню...")


def toggle_sound():
    """Перемикає звук"""
    game_settings["sound_enabled"] = not game_settings["sound_enabled"]
    if game_settings["sound_enabled"]:
        start_background_music()
        print("🔊 Звук увімкнено")
    else:
        stop_background_music()
        print("🔇 Звук вимкнено")


# === СТВОРЕННЯ КНОПОК МЕНЮ ===
menu_buttons = [
    Button(WIDTH // 2 - 100, 250, 200, 50, "Грати", start_game),
    Button(WIDTH // 2 - 100, 320, 200, 50, "Налаштування", open_settings),
    Button(WIDTH // 2 - 100, 390, 200, 50, "Вихід", exit_game)
]

settings_buttons = [
    Button(50, 500, 150, 40, "Назад", back_to_menu),
    Button(WIDTH - 200, 500, 150, 40, "Застосувати", back_to_menu),
    Button(350, 300, 150, 40, "Звук вкл/викл", toggle_sound)
]


# === ФУНКЦІЇ ВІДОБРАЖЕННЯ ===
def draw_menu():
    """Малює головне меню"""
    # Фон меню
    if menu_bg:
        screen.blit(menu_bg, (0, 0))
    else:
        screen.fill((30, 30, 60))

    # Заголовок
    title_text = font_title.render("ПІНГ-ПОНГ", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WIDTH // 2, 150))
    screen.blit(title_text, title_rect)

    # Підзаголовок
    subtitle_text = font_main.render("Онлайн гра для двох гравців", True, (200, 200, 200))
    subtitle_rect = subtitle_text.get_rect(center=(WIDTH // 2, 190))
    screen.blit(subtitle_text, subtitle_rect)

    # Кнопки
    for button in menu_buttons:
        button.draw(screen)


def draw_settings():
    """Малює меню налаштувань"""
    # Фон налаштувань
    if settings_bg:
        screen.blit(settings_bg, (0, 0))
    else:
        screen.fill((40, 40, 70))

    # Заголовок
    title_text = font_title.render("НАЛАШТУВАННЯ", True, (255, 255, 255))
    title_rect = title_text.get_rect(center=(WIDTH // 2, 80))
    screen.blit(title_text, title_rect)

    # Налаштування сервера
    y_offset = 150

    # IP сервера
    ip_label = font_main.render("IP сервера:", True, (255, 255, 255))
    screen.blit(ip_label, (100, y_offset))
    ip_value = font_main.render(game_settings["server_ip"], True, (200, 255, 200))
    screen.blit(ip_value, (300, y_offset))

    # Порт сервера
    y_offset += 50
    port_label = font_main.render("Порт:", True, (255, 255, 255))
    screen.blit(port_label, (100, y_offset))
    port_value = font_main.render(str(game_settings["server_port"]), True, (200, 255, 200))
    screen.blit(port_value, (300, y_offset))

    # Ім'я гравця
    y_offset += 50
    name_label = font_main.render("Ім'я гравця:", True, (255, 255, 255))
    screen.blit(name_label, (100, y_offset))
    name_value = font_main.render(game_settings["player_name"], True, (200, 255, 200))
    screen.blit(name_value, (300, y_offset))

    # Звук
    y_offset += 50
    sound_label = font_main.render("Звук:", True, (255, 255, 255))
    screen.blit(sound_label, (100, y_offset))
    sound_status = "Увімкнено" if game_settings["sound_enabled"] else "Вимкнено"
    sound_color = (200, 255, 200) if game_settings["sound_enabled"] else (255, 200, 200)
    sound_value = font_main.render(sound_status, True, sound_color)
    screen.blit(sound_value, (300, y_offset))

    # Підказка
    hint_text = font_small.render("Підказка: Змініть налаштування в коді для налаштування IP", True, (150, 150, 150))
    screen.blit(hint_text, (100, 400))

    # Кнопки
    for button in settings_buttons:
        button.draw(screen)


def draw_connecting():
    """Малює екран підключення"""
    # Фон
    if game_bg:
        screen.blit(game_bg, (0, 0))
    else:
        screen.fill((30, 30, 30))

    # Текст підключення
    connecting_text = font_title.render("Підключення...", True, (255, 255, 255))
    connecting_rect = connecting_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 - 50))
    screen.blit(connecting_text, connecting_rect)

    # Підтекст
    hint_text = font_main.render("Очікування з'єднання з сервером", True, (200, 200, 200))
    hint_rect = hint_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
    screen.blit(hint_text, hint_rect)

    # Інструкція
    instruction_text = font_small.render("Переконайтеся, що сервер запущено", True, (150, 150, 150))
    instruction_rect = instruction_text.get_rect(center=(WIDTH // 2, HEIGHT // 2 + 50))
    screen.blit(instruction_text, instruction_rect)

    # Кнопка назад
    back_button = Button(WIDTH // 2 - 75, HEIGHT // 2 + 100, 150, 40, "Назад", back_to_menu)
    back_button.hovered = back_button.rect.collidepoint(mouse.get_pos())
    back_button.draw(screen)

    return back_button


# === МЕРЕЖЕВІ ФУНКЦІЇ ===
def connect_to_server():
    """Підключення до сервера"""
    try:
        client = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        client.connect((game_settings["server_ip"], game_settings["server_port"]))
        buffer = ""
        game_state = {}
        my_id = int(client.recv(24).decode())
        return my_id, game_state, buffer, client
    except Exception as e:
        print(f"❌ Помилка підключення: {e}")
        return None


def receive():
    """Отримання даних від сервера"""
    global buffer, game_state, game_over
    while not game_over and current_state == PLAYING:
        try:
            data = client.recv(1024).decode()
            buffer += data
            while "\n" in buffer:
                packet, buffer = buffer.split("\n", 1)
                if packet.strip():
                    game_state = json.loads(packet)
        except:
            game_state["winner"] = -1
            break


# === ОСНОВНИЙ ІГРОВИЙ ЦИКЛ ===
# Ігрові змінні
game_over = False
winner = None
you_winner = None
my_id = None
game_state = {}
buffer = ""
client = None
connection_attempts = 0
last_sound_event = None

while True:
    # Обробка подій
    for e in event.get():
        if e.type == QUIT:
            stop_background_music()
            exit()

        # Обробка подій для різних станів
        if current_state == MENU:
            for button in menu_buttons:
                button.handle_event(e)

        elif current_state == SETTINGS:
            for button in settings_buttons:
                button.handle_event(e)

        elif current_state == CONNECTING:
            back_button = draw_connecting()  # Отримуємо кнопку для обробки
            back_button.handle_event(e)

    # === ВІДОБРАЖЕННЯ ВІДПОВІДНО ДО СТАНУ ===
    if current_state == MENU:
        draw_menu()

    elif current_state == SETTINGS:
        draw_settings()

    elif current_state == CONNECTING:
        draw_connecting()

        # Спроба підключення (не блокуюча)
        connection_attempts += 1
        if connection_attempts > 60:  # Спробувати підключитися через 1 секунду (60 кадрів)
            connection_attempts = 0
            result = connect_to_server()
            if result:
                my_id, game_state, buffer, client = result
                current_state = PLAYING
                game_over = False
                you_winner = None
                Thread(target=receive, daemon=True).start()
                print("✅ Успішно підключено до сервера!")

    elif current_state == PLAYING:
        # === ІГРОВА ЛОГІКА ===

        # Відображення фону
        if game_bg:
            screen.blit(game_bg, (0, 0))
        else:
            screen.fill((30, 30, 30))

        # Екран відліку
        if "countdown" in game_state and game_state["countdown"] > 0:
            countdown_text = font.Font(None, 72).render(str(game_state["countdown"]), True, (255, 255, 255))
            screen.blit(countdown_text, (WIDTH // 2 - 20, HEIGHT // 2 - 30))
            display.update()
            continue

        # Екран перемоги
        if "winner" in game_state and game_state["winner"] is not None:
            if win_bg:
                screen.blit(win_bg, (0, 0))
            else:
                screen.fill((20, 20, 20))

            if you_winner is None:
                if game_state["winner"] == my_id:
                    you_winner = True
                    play_sound_effect(win_sound)
                else:
                    you_winner = False
                    play_sound_effect(lose_sound)

            if you_winner:
                text = "Ти переміг!"
            else:
                text = "Пощастить наступним разом!"

            win_text = font_win.render(text, True, (255, 215, 0))
            text_rect = win_text.get_rect(center=(WIDTH // 2, HEIGHT // 2))
            screen.blit(win_text, text_rect)

            # Додаємо кнопку повернення до меню
            menu_button = Button(WIDTH // 2 - 100, HEIGHT // 2 + 80, 200, 50, "Головне меню", back_to_menu)
            menu_button.hovered = menu_button.rect.collidepoint(mouse.get_pos())
            menu_button.draw(screen)

            # Обробка кліку по кнопці меню
            for e in event.get():
                if e.type == QUIT:
                    stop_background_music()
                    exit()
                menu_button.handle_event(e)

            display.update()
            continue

        # Основна гра
        if game_state:
            # Ракетки
            if paddle1_img:
                screen.blit(paddle1_img, (20, game_state['paddles']['0']))
            else:
                draw.rect(screen, (0, 255, 0), (20, game_state['paddles']['0'], 20, 100))

            if paddle2_img:
                screen.blit(paddle2_img, (WIDTH - 40, game_state['paddles']['1']))
            else:
                draw.rect(screen, (255, 0, 255), (WIDTH - 40, game_state['paddles']['1'], 20, 100))

            # М'яч
            if ball_img:
                screen.blit(ball_img, (game_state['ball']['x'] - 10, game_state['ball']['y'] - 10))
            else:
                draw.circle(screen, (255, 255, 255), (game_state['ball']['x'], game_state['ball']['y']), 10)

            # Рахунок
            score_text = font_main.render(f"{game_state['scores'][0]} : {game_state['scores'][1]}", True,
                                          (255, 255, 255))
            screen.blit(score_text, (WIDTH // 2 - 25, 20))

            # Звукові події
            if game_state['sound_event'] and game_settings["sound_enabled"]:
                if game_state['sound_event'] == 'wall_hit':
                    play_sound_effect(wall_hit_sound)
                if game_state['sound_event'] == 'platform_hit':
                    play_sound_effect(paddle_hit_sound)
                    pass

        else:
            # Екран очікування
            waiting_text = font_main.render(f"Очікування гравців...", True, (255, 255, 255))
            screen.blit(waiting_text, (WIDTH // 2 - 125, HEIGHT // 2))

        # Управління
        keys = key.get_pressed()
        if keys[K_w] and client:
            try:
                client.send(b"UP")
            except:
                current_state = MENU  # Повернутися до меню при втраті з'єднання
        elif keys[K_s] and client:
            try:
                client.send(b"DOWN")
            except:
                current_state = MENU  # Повернутися до меню при втраті з'єднання

    display.update()
    clock.tick(60)