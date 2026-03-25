import telebot
from telebot import types
import random
import time
import json
import os

# --- [1] КОНФИГУРАЦИЯ ---
TOKEN = "8652514075:AAFYxclIzQ2uoNF7Ub0W3Yg24gL17gFt-p8"
ADMINS = ["verybigsun", "Nazikrrk"] 
bot = telebot.TeleBot(TOKEN)

FILES = {'cards': 'cards_data.json', 'colls': 'collections_data.json', 'users': 'users_stats.json'}

STATS = {
    1: {"score": 1000},
    2: {"score": 2000},
    3: {"score": 4000},
    4: {"score": 6000},
    5: {"score": 10000}
}

# --- [2] БД ФУНКЦИИ ---
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

def get_stars(count):
    return "⭐" * int(count)

# --- [3] КЛАВИАТУРЫ ---
def main_kb(user):
    markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
    markup.row("🎰 Крутить карту", "🗂 Коллекция")
    markup.row("👤 Профиль", "🏆 Топ игроков")
    markup.row("💎 Премиум")
    if user.username and user.username.lower() in [a.lower() for a in ADMINS]:
        markup.add("🛠 Админ-панель")
    return markup

# --- [4] ЛОГИКА ИГРЫ ---

@bot.message_handler(commands=['start'])
def start(m):
    uid = str(m.from_user.id)
    users = load_db('users')
    if uid not in users:
        users[uid] = {"score": 0, "username": m.from_user.username or f"user_{uid}"}
        save_db(users, 'users')
    bot.send_message(m.chat.id, "👋 Привет! Это бот СЛС карточек.", reply_markup=main_kb(m.from_user))

@bot.message_handler(func=lambda m: m.text == "🏆 Топ игроков")
def top_players(m):
    users = load_db('users')
    sorted_users = sorted(users.items(), key=lambda x: x[1]['score'], reverse=True)
    text = "🏆 **ТОП-10 ИГРОКОВ:**\n\n"
    for i, (uid, data) in enumerate(sorted_users[:10], 1):
        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
        text += f"{medal} @{data['username']} — `{data['score']:,}` очков\n"
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🗂 Коллекция")
def my_collection(m):
    uid = str(m.from_user.id)
    colls = load_db('colls')
    my_cards = colls.get(uid, [])
    if not my_cards:
        return bot.send_message(m.chat.id, "🗂 Ваша коллекция пока пуста!")
    text = f"🗂 **ВАША КОЛЛЕКЦИЯ ({len(my_cards)} шт.):**\n\n"
    for card in my_cards:
        text += f"• {card['name']} ({get_stars(card['stars'])})\n"
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "🎰 Крутить карту")
def roll(m):
    uid = str(m.from_user.id)
    cards = load_db('cards')
    users = load_db('users')
    colls = load_db('colls')
    if not cards: return bot.send_message(m.chat.id, "❌ В игре пока нет карточек!")
    won = random.choice(cards)
    if uid not in colls: colls[uid] = []
    is_new = not any(c['name'] == won['name'] for c in colls[uid])
    base_pts = STATS.get(int(won.get('stars', 1)), {"score": 500})["score"]
    added_pts = base_pts if is_new else int(base_pts * 0.3)
    users[uid]['score'] += int(added_pts)
    if is_new:
        colls[uid].append(won)
        save_db(colls, 'colls')
    save_db(users, 'users')
    status = "🆕 Новая карта!" if is_new else "♻️ Повторка"
    caption = (
        f"⚽️ **{won['name']}** ({status})\n"
        f" — — — — — — — — — —\n"
        f"🎯 **Позиция:** `{won.get('pos', '—')}`\n"
        f"📊 **Рейтинг:** {get_stars(won.get('stars', 1))}\n"
        f" — — — — — — — — — —\n"
        f"💠 **Очки:** `+{int(added_pts):,}` | Всего: `{users[uid]['score']:,}`"
    )
    bot.send_photo(m.chat.id, won['photo'], caption=caption, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "👤 Профиль")
def profile(m):
    uid = str(m.from_user.id)
    u = load_db('users').get(uid, {"score": 0})
    c = len(load_db('colls').get(uid, []))
    text = f"👤 **ВАШ ПРОФИЛЬ**\n — — —\n🆔 ID: `{uid}`\n💠 Очки: `{u['score']:,}`\n🗂 Коллекция: `{c}` шт."
    bot.send_message(m.chat.id, text, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "💎 Премиум")
def prem(m):
    bot.send_message(m.chat.id, "💎 **Премиум статус**\n\n• Крутки без КД\n✉️ Купить: @verybigsun", parse_mode="Markdown")

# --- [5] АДМИНКА (ИСПРАВЛЕНА) ---
@bot.message_handler(func=lambda m: m.text == "🛠 Админ-панель")
def adm(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        markup = types.ReplyKeyboardMarkup(resize_keyboard=True)
        markup.row("➕ Добавить карту", "🗑 Удалить карту")
        markup.row("🏠 Назад в меню")
        bot.send_message(m.chat.id, "🛠 Панель управления администратора:", reply_markup=markup)

@bot.message_handler(func=lambda m: m.text == "🗑 Удалить карту")
def delete_menu(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        cards = load_db('cards')
        if not cards:
            return bot.send_message(m.chat.id, "❌ База карт пуста.")
        
        markup = types.InlineKeyboardMarkup()
        for c in cards:
            # Создаем кнопку для каждой карты
            markup.add(types.InlineKeyboardButton(f"❌ Удалить {c['name']}", callback_data=f"del_{c['name']}"))
        
        bot.send_message(m.chat.id, "Выберите карту, которую нужно удалить:", reply_markup=markup)

@bot.callback_query_handler(func=lambda call: call.data.startswith("del_"))
def process_delete(call):
    name_to_delete = call.data.replace("del_", "")
    cards = load_db('cards')
    
    # Фильтруем список, оставляя все кроме выбранной карты
    new_cards = [c for c in cards if c['name'] != name_to_delete]
    save_db(new_cards, 'cards')
    
    bot.answer_callback_query(call.id, f"Карта {name_to_delete} удалена")
    bot.edit_message_text(f"✅ Карта **{name_to_delete}** успешно удалена из базы.", call.message.chat.id, call.message.message_id, parse_mode="Markdown")

@bot.message_handler(func=lambda m: m.text == "➕ Добавить карту")
def add_start(m):
    if m.from_user.username and m.from_user.username.lower() in [a.lower() for a in ADMINS]:
        msg = bot.send_message(m.chat.id, "Введите ИМЯ игрока:")
        bot.register_next_step_handler(msg, add_step_stars)

def add_step_stars(m):
    name = m.text
    msg = bot.send_message(m.chat.id, f"Введите РЕЙТИНГ (число от 1 до 5) для {name}:")
    bot.register_next_step_handler(msg, add_step_pos, name)

def add_step_pos(m, name):
    stars = m.text
    msg = bot.send_message(m.chat.id, f"Введите ПОЗИЦИЮ игрока (например, Нападающий):")
    bot.register_next_step_handler(msg, add_step_photo, name, stars)

def add_step_photo(m, name, stars):
    pos = m.text
    msg = bot.send_message(m.chat.id, f"Отправьте ФОТО для карты {name}:")
    bot.register_next_step_handler(msg, add_final, name, stars, pos)

def add_final(m, name, stars, pos):
    if not m.photo:
        return bot.send_message(m.chat.id, "❌ Нужно отправить именно фото. Попробуйте снова.")
    cards = load_db('cards')
    cards.append({
        "name": name, 
        "stars": int(stars) if stars.isdigit() else 1, 
        "pos": pos, 
        "photo": m.photo[-1].file_id
    })
    save_db(cards, 'cards')
    bot.send_message(m.chat.id, f"✅ Карта {name} успешно добавлена!", reply_markup=main_kb(m.from_user))

@bot.message_handler(func=lambda m: m.text == "🏠 Назад в меню")
def back(m):
    bot.send_message(m.chat.id, "Возвращаю в главное меню...", reply_markup=main_kb(m.from_user))

bot.infinity_polling()
