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
        res = {} if key in ['users', 'colls'] else []
        save_db(res, key)
        return res
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try: return json.load(f)
        except: return {} if key in ['users', 'colls'] else []

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

cards = load_db('cards')
user_colls = load_db('colls')
users_data = load_db('users')
cooldowns = {}

# --- [3] КЛАВІАТУРА ---
def main_kb(user):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутити карту", "🗂 Коллекция")
    markup.row("👤 Профіль", "🏆 Топ по очкам")
    if user.username and user.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОБРОБНИКИ ---

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    if uid not in users_data:
        users_data[uid] = {"score": 0, "username": m.from_user.username or f"user_{uid}"}
        save_db(users_data, 'users')
    bot.send_message(m.chat.id, "⚽️ Бот запущений!", reply_markup=main_kb(m.from_user))

# ФУНКЦІЯ ПРОФІЛЮ
@bot.message_handler(func=lambda m: m.text and "Профіль" in m.text)
def profile(m):
    uid = str(m.from_user.id)
    u = users_data.get(uid, {"score": 0, "username": "Гість"})
    col = len(user_colls.get(uid, []))
    txt = f"👤 *ПРОФІЛЬ:*\n\nID: `{uid}`\nНік: @{u['username']}\nОчки: `{u['score']:,}`\nКарт: `{col}`"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# ГОЛОВНА ФУНКЦІЯ: КРУТИТИ КАРТУ
@bot.message_handler(func=lambda m: m.text and "Крутити" in m.text)
def roll(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    # Перевірка адміна для КД
    is_adm = m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]
    
    if not is_adm:
        if uid in cooldowns and now - cooldowns[uid] < 10800:
            rem = int(10800 - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ КД! Зачекай {rem//3600}г {(rem%3600)//60}хв")

    if not cards:
        return bot.send_message(m.chat.id, "❌ Адмін ще не додав жодної карти!")

    # Рандом зірок
    s_roll = random.choices(list(STATS.keys()), weights=[s['chance'] for s in STATS.values()])[0]
    pool = [c for c in cards if int(c.get('stars', 1)) == s_roll]
    won = random.choice(pool if pool else cards)
    
    cooldowns[uid] = now
    if uid not in user_colls: user_colls[uid] = []
    
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    # Очки (30% за повторку)
    pts = int(STATS[int(won.get('stars', 1))]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
    
    users_data[uid]['score'] += pts
    save_db(users_data, 'users')
    
    msg = f"⚽️ *{won['name']}*\n⭐ Рейтинг: {won.get('stars', '?')}\n🎯 Поз: {won.get('pos', '?')}\n\n💠 Очки: +{pts:,} (Разом: {users_data[uid]['score']:,})"
    bot.send_photo(m.chat.id, won['photo'], caption=msg, parse_mode="Markdown")

# --- [5] АДМІНКА (НОВИЙ ПОРЯДОК: Назва -> Рейтинг -> Позиція -> Фото) ---

@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_p(m):
    kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
    kb.add("➕ Добавить карту", "🏠 Назад в меню")
    bot.send_message(m.chat.id, "Панель керування:", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_1(m):
    msg = bot.send_message(m.chat.id, "📌 Введіть НАЗВУ (прізвище гравця):")
    bot.register_next_step_handler(msg, add_2)

def add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"🌟 Введіть РЕЙТИНГ (1-5 зірок) для {name}:")
    bot.register_next_step_handler(msg, add_3, name)

def add_3(m, name):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, f"🎯 Введіть ПОЗИЦІЮ (ST, GK, LW...):")
        bot.register_next_step_handler(msg, add_4, name, stars)
    except:
        bot.send_message(m.chat.id, "❌ Потрібно число!")

def add_4(m, name, stars):
    pos = m.text
    msg = bot.send_message(m.chat.id, f"📸 Надішліть ФОТО для {name}:")
    bot.register_next_step_handler(msg, add_fin, name, stars, pos)

def add_fin(m, name, stars, pos):
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Ви не надіслали фото!")
    cards.append({"name": name, "stars": stars, "pos": pos, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Успішно! Карта {name} додана.")

@bot.message_handler(func=lambda m: "Назад" in m.text)
def back(m):
    bot.send_message(m.chat.id, "Меню:", reply_markup=main_kb(m.from_user))

bot.infinity_polling()
