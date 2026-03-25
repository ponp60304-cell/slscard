import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФІГУРАЦІЯ ---
# Твій новий токен:
TOKEN = "8316043913:AAFJFjGapMK62ktJD3LhhPphceJ1BBi_P4A"
ADMINS = ["verybigsun", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

FILES = {
    'cards': 'cards_data.json', 
    'colls': 'collections_data.json', 
    'users': 'users_stats.json'
}

STATS = {
    1: {"chance": 40, "score": 1000},
    2: {"chance": 30, "score": 2000},
    3: {"chance": 20, "score": 4000},
    4: {"chance": 10, "score": 6000},
    5: {"chance": 5, "score": 10000}
}

# --- [2] БД ФУНКЦІЇ ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        res = {} if key in ['users', 'colls'] else []
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(res, f, ensure_ascii=False, indent=4)
        return res
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return {} if key in ['users', 'colls'] else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

cooldowns = {}

# --- [3] КЛАВІАТУРА ---
def main_kb(user):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутити карту", "🗂 Коллекция")
    markup.row("👤 Профіль", "🏆 Топ по очкам") # Кнопка профіль тепер тут
    
    is_adm = False
    if user.username and user.username.lower() in [a.lower() for a in ADMINS]:
        is_adm = True
    
    if is_adm:
        markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОБРОБНИКИ ОСНОВНИХ КОМАНД ---

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    users_data = load_db('users')
    
    if uid not in users_data:
        users_data[uid] = {"score": 0, "username": m.from_user.username or f"user_{uid}"}
        save_db(users_data, 'users')
    
    # Текст для перевірки оновлення
    bot.send_message(m.chat.id, "♻️ БОТ ОНОВЛЕНИЙ (НОВИЙ ТОКЕН)!\nВсі системи готові до роботи.", reply_markup=main_kb(m.from_user))

@bot.message_handler(func=lambda m: m.text and "Профіль" in m.text)
def profile(m):
    uid = str(m.from_user.id)
    users_data = load_db('users')
    user_colls = load_db('colls')
    u = users_data.get(uid, {"score": 0, "username": "Гість"})
    col = len(user_colls.get(uid, []))
    
    txt = (f"👤 *ТВІЙ ПРОФІЛЬ:*\n\n"
           f"🆔 ID: `{uid}`\n"
           f"💠 Очки: `{u['score']:,}`\n"
           f"🗂 Карт у колекції: `{col}`")
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text and "Крутити" in m.text)
def roll(m):
    uid = str(m.from_user.id)
    cards = load_db('cards')
    users_data = load_db('users')
    user_colls = load_db('colls')

    if not cards:
        return bot.send_message(m.chat.id, "❌ У базі ще немає карт. Додай їх через адмін-панель!")

    # Рандомний вибір карти
    won = random.choice(cards)
    
    # Логіка очок (спрощена для тесту)
    pts = 1000
    users_data[uid]['score'] += pts
    save_db(users_data, 'users')
    
    bot.send_photo(m.chat.id, won['photo'], caption=f"⚽️ Вітаємо! Ви вибили карту: *{won['name']}*\n\n💠 Очки: +{pts}", parse_mode="Markdown")

# --- [5] АДМІН-СИСТЕМА (Назва -> Рейтинг -> Позиція -> Фото) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    # Перевірка адміна ще раз для безпеки
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("➕ Добавить карту", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 Панель керування:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_1(m):
    msg = bot.send_message(m.chat.id, "1️⃣ Введіть НАЗВУ гравця:")
    bot.register_next_step_handler(msg, add_2)

def add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, "2️⃣ Введіть РЕЙТИНГ (1-5 зірок):")
    bot.register_next_step_handler(msg, add_3, name)

def add_3(m, name):
    stars = m.text
    msg = bot.send_message(m.chat.id, "3️⃣ Введіть ПОЗИЦІЮ (ST, GK, LW...):")
    bot.register_next_step_handler(msg, add_4, name, stars)

def add_4(m, name, stars):
    pos = m.text
    msg = bot.send_message(m.chat.id, "4️⃣ Надішліть ФОТО для цієї карти:")
    bot.register_next_step_handler(msg, add_fin, name, stars, pos)

def add_fin(m, name, stars, pos):
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Потрібно надіслати фото! Спробуй ще раз.")
    
    cards = load_db('cards')
    cards.append({
        "name": name, 
        "stars": int(stars) if stars.isdigit() else 1, 
        "pos": pos, 
        "photo": m.photo[-1].file_id
    })
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} успішно додана!", reply_markup=main_kb(m.from_user))

@bot.message_handler(func=lambda m: "Назад" in m.text)
def back(m):
    bot.send_message(m.chat.id, "Головне меню:", reply_markup=main_kb(m.from_user))

print("Бот запущений на новому токені...")
bot.infinity_polling()
