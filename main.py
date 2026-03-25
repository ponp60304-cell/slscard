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

# --- [2] РОБОТА З БАЗОЮ ДАННИХ ---
def load_db(key):
    if not os.path.exists(FILES[key]):
        default = [] if key != 'users' else {}
        with open(FILES[key], 'w', encoding='utf-8') as f:
            json.dump(default, f, ensure_ascii=False, indent=4)
        return default
    with open(FILES[key], 'r', encoding='utf-8') as f:
        try:
            return json.load(f)
        except:
            return [] if key != 'users' else {}

def save_db(data, key):
    with open(FILES[key], 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# Ініціалізація даних
cards = load_db('cards')
user_colls = load_db('colls')
users_data = load_db('users')
cooldowns = {}

# --- [3] ДОПОМІЖНІ ФУНКЦІЇ ---
def is_admin(user):
    return user.username and user.username.lower() in [a.lower() for a in ADMINS]

def main_kb(user):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    # Важливо: текст тут має точно збігатися з текстом у @bot.message_handler
    markup.row("🎰 Крутити карту", "🗂 Коллекция")
    markup.row("🏆 Топ по очкам")
    if is_admin(user):
        markup.add("🛠 Админ-панель")
    return markup

# --- [4] ОБРОБКА КОМАНД ---
@bot.message_handler(commands=['start'])
def start_command(message):
    uid = str(message.from_user.id)
    if uid not in users_data:
        users_data[uid] = {
            "score": 0, 
            "username": message.from_user.username or f"user_{uid}"
        }
        save_db(users_data, 'users')
    bot.send_message(message.chat.id, "⚽️ Бот готовий до роботи!", reply_markup=main_kb(message.from_user))

# --- [5] ЛОГІКА КРУТКИ КАРТ ---
@bot.message_handler(func=lambda m: m.text == "🎰 Крутити карту")
def roll_card(m):
    uid = str(m.from_user.id)
    now = time.time()
    
    # Перевірка КД (3 години = 10800 сек)
    if not is_admin(m.from_user):
        if uid in cooldowns and now - cooldowns[uid] < 10800:
            left = int(10800 - (now - cooldowns[uid]))
            return bot.send_message(m.chat.id, f"⏳ КД! Чекай ще `{left // 3600}г {(left % 3600) // 60}хв`", parse_mode="Markdown")

    if not cards:
        return bot.send_message(m.chat.id, "❌ У базі ще немає карт. Попроси адмінів додати їх!")

    # Вибір рідкості
    stars_list = list(STATS.keys())
    weights = [STATS[s]['chance'] for s in stars_list]
    chosen_stars = random.choices(stars_list, weights=weights)[0]
    
    # Фільтруємо карти за випавшою рідкістю
    pool = [c for c in cards if int(c['stars']) == chosen_stars]
    if not pool: # Якщо карт такої рідкості немає, беремо будь-яку
        won = random.choice(cards)
    else:
        won = random.choice(pool)

    cooldowns[uid] = now
    
    if uid not in user_colls: 
        user_colls[uid] = []
    
    # Перевірка на дублікат
    is_dub = any(c['name'] == won['name'] for c in user_colls[uid])
    pts = int(STATS[won['stars']]['score'] * (0.3 if is_dub else 1))
    
    if not is_dub:
        user_colls[uid].append(won)
        save_db(user_colls, 'colls')
    
    users_data[uid]['score'] += pts
    users_data[uid]['username'] = m.from_user.username or f"user_{uid}"
    save_db(users_data, 'users')
    
    status = "ПОВТОРКА" if is_dub else "НОВА КАРТА"
    cap = (
        f"⚽️ *{won['name']}* (\"{status}\")\n\n"
        f"🎯 **Позиція:** {won['pos']}\n"
        f"📊 **Рейтинг:** {'⭐' * won['stars']}\n\n"
        f"💠 **Очки:** +{pts:,} | Всього: {users_data[uid]['score']:,}"
    )
    
    try:
        bot.send_photo(m.chat.id, won['photo'], caption=cap, parse_mode="Markdown")
    except Exception as e:
        bot.send_message(m.chat.id, f"Помилка відправки фото: {e}\n\n{cap}", parse_mode="Markdown")

# --- [6] ТОП ПО ОЧКАХ ---
@bot.message_handler(func=lambda m: m.text == "🏆 Топ по очкам")
def show_top(m):
    top_list = sorted(users_data.values(), key=lambda x: x['score'], reverse=True)[:10]
    txt = "🏆 **ТОП-10 ГРАВЦІВ:**\n\n"
    for i, user in enumerate(top_list, 1):
        name = f"@{user['username']}" if not str(user['username']).startswith("user_") else user['username']
        txt += f"{i}. {name} — `{user['score']:,}`\n"
    bot.send_message(m.chat.id, txt, parse_mode="Markdown")

# --- [7] КОЛЕКЦІЯ ---
@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def collection_menu(m):
    kb = types.InlineKeyboardMarkup()
    for i in range(1, 6):
        kb.add(types.InlineKeyboardButton("⭐" * i, callback_data=f"stars_{i}"))
    bot.send_message(m.chat.id, "🗂 Твоя колекція за рейтингом:", reply_markup=kb)

@bot.callback_query_handler(func=lambda c: c.data.startswith("stars_"))
def view_stars(call):
    s = int(call.data.split("_")[1])
    uid = str(call.from_user.id)
    my_cards = [c for c in user_colls.get(uid, []) if int(c['stars']) == s]
    
    if not my_cards:
        return bot.answer_callback_query(call.id, "У тебе немає таких карт!", show_alert=True)
    
    txt = f"🗂 **Карти {s}⭐:**\n\n" + "\n".join([f"• {c['name']} ({c['pos']})" for c in my_cards])
    bot.send_message(call.message.chat.id, txt, parse_mode="Markdown")
    bot.answer_callback_query(call.id)

# --- [8] АДМІН-ПАНЕЛЬ ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def admin_panel(m):
    if is_admin(m.from_user):
        kb = types.ReplyKeyboardMarkup(resize_keyboard=True)
        kb.row("➕ Добавить карту", "🗑 Удалить карту", "📝 Изменить карту")
        kb.add("🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 **Адмін-панель:**", reply_markup=kb)

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def adm_add_1(m):
    if not is_admin(m.from_user): return
    msg = bot.send_message(m.chat.id, "Введіть ім'я гравця:")
    bot.register_next_step_handler(msg, adm_add_2)

def adm_add_2(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Позиція для {name}:")
    bot.register_next_step_handler(msg, adm_add_3, name)

def adm_add_3(m, name):
    pos = m.text
    msg = bot.send_message(m.chat.id, "Кількість зірок (1-5):")
    bot.register_next_step_handler(msg, adm_add_4, name, pos)

def adm_add_4(m, name, pos):
    try:
        stars = int(m.text)
        msg = bot.send_message(m.chat.id, "Надішліть фото карти:")
        bot.register_next_step_handler(msg, adm_add_fin, name, pos, stars)
    except:
        bot.send_message(m.chat.id, "Помилка! Введіть число.")

def adm_add_fin(m, name, pos, stars):
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Це не фото!")
    cards.append({"name": name, "pos": pos, "stars": stars, "photo": m.photo[-1].file_id})
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта **{name}** додана!")

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back_home(m):
    bot.send_message(m.chat.id, "Головне меню:", reply_markup=main_kb(m.from_user))

if __name__ == '__main__':
    print("Бот запущений...")
    bot.infinity_polling()
