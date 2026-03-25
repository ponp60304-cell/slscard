import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФІГУРАЦІЯ ---
TOKEN = "8728235198:AAGMHfBZw0UCnOk_0DUsB7VbDt8fiWua8Ik"
ADMINS = ["verybigsun", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

FILES = {'cards': 'cards_data.json', 'colls': 'collections_data.json', 'users': 'users_stats.json'}

STATS = {
    1: {"chance": 40, "score": 1000},
    2: {"chance": 30, "score": 2000},
    3: {"chance": 20, "score": 4000},
    4: {"chance": 10, "score": 6000},
    5: {"chance": 5, "score": 10000}
}

# --- [2] БД ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        res = {} if key == 'users' or key == 'colls' else []
        save_db(res, key)
        return res
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return {} if key == 'users' or key == 'colls' else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

cards = load_db('cards')
user_colls = load_db('colls')
users_data = load_db('users')
cooldowns = {}

# --- [3] ФУНКЦІЇ ---
def is_admin(user):
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def main_kb(user):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутити карту", "🗂 Коллекция")
    markup.row("🏆 Топ по очкам")
    if is_admin(user):
        markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОБРОБКА ---
@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        users_data[uid] = {"score": 0, "username": m.from_user.username or f"user_{uid}"}
        save_db(users_data, 'users')
    bot.send_message(m.chat.id, "⚽️ Бот готовий!", reply_markup=main_kb(m.from_user))

# ВИПРАВЛЕНО: Більш гнучка перевірка натискання кнопки
@bot.message_handler(func=lambda m: "Крутити карту" in m.text)
def roll_card(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < 10800:
            left = int(10800 - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ КД! Жди: `{left//3600}г {(left%3600)//60}хв`", parse_mode="Markdown")

    if not cards:
        return bot.send_message(m.chat.id, "❌ Карт немає в базі!")

    # Логіка шансів
    stars = random.choices(list(STATS.keys()), weights=[s['chance'] for s in STATS.values()])[0]
    pool = [c for c in cards if int(c['stars']) == stars]
    won = random.choice(pool if pool else cards)
    
    cooldowns[uid] = now
    if uid not in user_colls: user_colls[uid] = []
    
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    pts = int(STATS[int(won['stars'])]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
    
    users_data[uid]['score'] += pts
    save_db(users_data, 'users')
    
    status = "ПОВТОРКА" if is_dub else "НОВА"
    cap = f"⚽️ *{won['name']}* ({status})\n⭐ Рейтинг: {won['stars']}\n🎯 Позиція: {won['pos']}\n💠 Очки: +{pts}"
    bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")

# --- [5] НОВА СИСТЕМА ДОДАВАННЯ (Назва -> Рейтинг -> Позиція -> Фото) ---
@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_step_1(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "1️⃣ Введіть НАЗВУ гравця:")
    bot.register_next_step_handler(msg, add_step_2)

def add_step_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"2️⃣ Введіть РЕЙТИНГ (1-5 зірок) для {name}:")
    bot.register_next_step_handler(msg, add_step_3, name)

def add_step_3(m, name):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, f"3️⃣ Введіть ПОЗИЦІЮ (напр. ST, GK, LW):")
        bot.register_next_step_handler(msg, add_step_4, name, stars)
    except:
        bot.send_message(m.chat.id, "❌ Треба ввести число! Спробуйте ще раз через меню.")

def add_step_4(m, name, stars):
    pos = m.text
    msg = bot.send_message(m.chat.id, f"4️⃣ Надішліть ФОТО для карти {name}:")
    bot.register_next_step_handler(msg, add_step_fin, name, stars, pos)

def add_step_fin(m, name, stars, pos):
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Це не фото! Спробуйте спочатку.")
    
    cards.append({
        "name": name,
        "stars": stars,
        "pos": pos,
        "photo": m.photo[-1].file_id
    })
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} ({stars}⭐) додана успішно!", reply_markup=main_kb(m.from_user))

# --- ІНШІ КОМАНДИ ---
@bot.message_handler(func=lambda m: "Топ по очкам" in m.text)
def top(m):
    top_list = sorted(users_data.values(), key=lambda x: x['score'], reverse=True)[:10]
    res = "🏆 **ТОП-10:**\n\n"
    for i, u in enumerate(top_list, 1):
        res += f"{i}. {u['username']} — `{u['score']}`\n"
    bot.send_message(m.chat.id, res, parse_mode="Markdown")

@bot.message_handler(func=lambda m: "Админ-панель" in m.text)
def adm(m):
    if is_admin(m.from_user):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.add("➕ Добавить карту", "🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 Адмінка:", reply_markup=kb)

@bot.message_handler(func=lambda m: "Назад в меню" in m.text)
def back(m):
    bot.send_message(m.chat.id, "Головне меню:", reply_markup=main_kb(m.from_user))

bot.infinity_polling()
