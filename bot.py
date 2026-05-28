
import json
import os
import random
import re
from difflib import SequenceMatcher
from pathlib import Path

from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import Application, CommandHandler, MessageHandler, ContextTypes, filters

BOT_TOKEN = os.getenv("BOT_TOKEN")
BASE = Path(__file__).resolve().parent

with open(BASE / "bg_chapter1_questions_full.json", "r", encoding="utf-8") as f:
    DB = json.load(f)

QUESTIONS = DB["questions"]
CARDS = DB["cards"]
USER = {}

TEXT = {
    "RU": {
        "welcome": "🌿 Живая Гита\n\nВыберите режим:",
        "menu": "Главное меню",
        "study_intro": "📖 Изучение\n\nПокажу карточки первой главы. Сначала вспомните ответ, затем нажмите кнопку под карточкой.",
        "card": "🃏 Карточка",
        "answer": "✅ Правильный ответ:",
        "done_study": "✅ Сессия изучения завершена",
        "test_intro": "🧠 Тест\n\nВопросы будут разного уровня: варианты ответа и ручной ввод.",
        "test": "🧠 Тест",
        "write": "✍️ Напиши ответ",
        "right": "✅ Верно",
        "wrong": "❌ Неверно",
        "done_test": "🏁 Тест завершён",
        "use_buttons": "В режиме изучения используйте кнопки под карточкой.",
        "settings_text": "⚙ Настройки\n\nВыберите язык, уровень или диапазон.",
        "scope_hint": "Введите диапазон\nнапример: 1.1, 1.1–1.5, Глава 1",
        "scope_saved": "✅ Диапазон сохранён:",
        "level_saved": "✅ Уровень теста:",
        "lang_ru": "✅ Язык: Русский",
        "lang_en": "✅ Language: English",
        "lang_both": "✅ Режим: RU + EN",
        "unknown": "Я не распознал сообщение. Выберите действие в меню ниже.",
    },
    "EN": {
        "welcome": "🌿 Living Gita\n\nChoose a mode:",
        "menu": "Main menu",
        "study_intro": "📖 Study\n\nI will show Chapter 1 cards. First remember the answer, then press a button under the card.",
        "card": "🃏 Card",
        "answer": "✅ Correct answer:",
        "done_study": "✅ Study session completed",
        "test_intro": "🧠 Test\n\nQuestions include different levels: multiple choice and written answers.",
        "test": "🧠 Test",
        "write": "✍️ Write the answer",
        "right": "✅ Correct",
        "wrong": "❌ Incorrect",
        "done_test": "🏁 Test completed",
        "use_buttons": "In Study mode, please use the buttons under the card.",
        "settings_text": "⚙ Settings\n\nChoose language, level, or range.",
        "scope_hint": "Enter a range\nexample: 1.1, 1.1–1.5, Chapter 1",
        "scope_saved": "✅ Range saved:",
        "level_saved": "✅ Test level:",
        "lang_ru": "✅ Язык: Русский",
        "lang_en": "✅ Language: English",
        "lang_both": "✅ Mode: RU + EN",
        "unknown": "I did not recognize the message. Please choose an action from the menu below.",
    },
    "BOTH": {
        "welcome": "🌿 Живая Гита / Living Gita\n\nВыберите режим / Choose a mode:",
        "menu": "Главное меню / Main menu",
        "study_intro": "📖 Изучение / Study\n\nПокажу карточки. First remember the answer, then press a button.",
        "card": "🃏 Карточка / Card",
        "answer": "✅ Правильный ответ / Correct answer:",
        "done_study": "✅ Сессия изучения завершена / Study session completed",
        "test_intro": "🧠 Тест / Test\n\nБудут варианты ответа и ручной ввод / Multiple choice and written answers.",
        "test": "🧠 Тест / Test",
        "write": "✍️ Напиши ответ / Write the answer",
        "right": "✅ Верно / Correct",
        "wrong": "❌ Неверно / Incorrect",
        "done_test": "🏁 Тест завершён / Test completed",
        "use_buttons": "В режиме изучения используйте кнопки. / In Study mode, please use buttons.",
        "settings_text": "⚙ Настройки / Settings\n\nВыберите язык, уровень или диапазон.",
        "scope_hint": "Введите диапазон / Enter a range\nнапример / example: 1.1, 1.1–1.5, Глава 1",
        "scope_saved": "✅ Диапазон сохранён / Range saved:",
        "level_saved": "✅ Уровень теста / Test level:",
        "lang_ru": "✅ Язык: Русский",
        "lang_en": "✅ Language: English",
        "lang_both": "✅ Режим: RU + EN",
        "unknown": "Я не распознал сообщение / I did not recognize the message. Выберите действие ниже.",
    }
}

def get_state(uid):
    USER.setdefault(uid, {
        "lang": "RU",
        "level": 1,
        "scope": "Глава 1",
        "mode": None,
        "queue": [],
        "current": None,
        "xp": 0,
        "correct": 0,
        "total": 0,
        "session_correct": 0,
        "session_total": 0,
    })
    return USER[uid]

def tx(st, key):
    return TEXT.get(st["lang"], TEXT["RU"])[key]

def main_menu(st):
    if st["lang"] == "EN":
        rows = [
            [KeyboardButton("📖 Study"), KeyboardButton("🧠 Test")],
            [KeyboardButton("🔥 Daily Practice"), KeyboardButton("📊 Progress")],
            [KeyboardButton("⚙ Settings")]
        ]
    elif st["lang"] == "BOTH":
        rows = [
            [KeyboardButton("📖 Изучение / Study"), KeyboardButton("🧠 Тест / Test")],
            [KeyboardButton("🔥 Daily Practice"), KeyboardButton("📊 Прогресс / Progress")],
            [KeyboardButton("⚙ Настройки / Settings")]
        ]
    else:
        rows = [
            [KeyboardButton("📖 Изучение"), KeyboardButton("🧠 Тест")],
            [KeyboardButton("🔥 Daily Practice"), KeyboardButton("📊 Прогресс")],
            [KeyboardButton("⚙ Настройки")]
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False, input_field_placeholder="Выберите действие")

def study_menu(st):
    if st["lang"] == "EN":
        rows = [
            [KeyboardButton("✅ I know"), KeyboardButton("🤔 Not sure")],
            [KeyboardButton("❌ I don’t know"), KeyboardButton("➡️ Next card")],
            [KeyboardButton("⬅️ Menu")]
        ]
    elif st["lang"] == "BOTH":
        rows = [
            [KeyboardButton("✅ Знаю / I know"), KeyboardButton("🤔 Затрудняюсь / Not sure")],
            [KeyboardButton("❌ Не знаю / I don’t know"), KeyboardButton("➡️ Следующая карточка / Next card")],
            [KeyboardButton("⬅️ Меню / Menu")]
        ]
    else:
        rows = [
            [KeyboardButton("✅ Знаю"), KeyboardButton("🤔 Затрудняюсь")],
            [KeyboardButton("❌ Не знаю"), KeyboardButton("➡️ Следующая карточка")],
            [KeyboardButton("⬅️ Меню")]
        ]
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False, input_field_placeholder="Выберите кнопку")

def settings_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English"), KeyboardButton("🌍 RU + EN")],
        [KeyboardButton("Уровень 1"), KeyboardButton("Уровень 2")],
        [KeyboardButton("📚 Выбор стихов / Verse scope")],
        [KeyboardButton("⬅️ Меню / Menu")]
    ], resize_keyboard=True, one_time_keyboard=False)

def answer_keyboard(options):
    rows = [[KeyboardButton(opt)] for opt in options]
    rows.append([KeyboardButton("⬅️ Меню / Menu")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True, one_time_keyboard=False)

def scope_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("1.1"), KeyboardButton("1.1–1.5")],
        [KeyboardButton("Глава 1"), KeyboardButton("Вся Гита")],
        [KeyboardButton("⬅️ Меню / Menu")]
    ], resize_keyboard=True, one_time_keyboard=False)

def menu_pressed(s): return s in ["⬅️ Меню", "⬅️ Menu", "⬅️ Меню / Menu", "/menu", "меню", "Menu"]
def study_pressed(s): return s in ["📖 Изучение", "📖 Study", "📖 Изучение / Study"]
def test_pressed(s): return s in ["🧠 Тест", "🧠 Test", "🧠 Тест / Test"]
def progress_pressed(s): return s in ["📊 Прогресс", "📊 Progress", "📊 Прогресс / Progress"]
def settings_pressed(s): return s in ["⚙ Настройки", "⚙ Settings", "⚙ Настройки / Settings"]
def daily_pressed(s): return s == "🔥 Daily Practice"
def card_response(s):
    return s in [
        "✅ Знаю","🤔 Затрудняюсь","❌ Не знаю",
        "✅ I know","🤔 Not sure","❌ I don’t know",
        "✅ Знаю / I know","🤔 Затрудняюсь / Not sure","❌ Не знаю / I don’t know"
    ]
def next_pressed(s): return s in ["➡️ Следующая карточка", "➡️ Next card", "➡️ Следующая карточка / Next card"]

def normalize(s):
    if s is None: return ""
    s = s.lower().strip()
    repl = {"ṣ":"s","ś":"s","ā":"a","ī":"i","ū":"u","ṛ":"r","ṅ":"n","ñ":"n","ṭ":"t","ḍ":"d","ḥ":"h","ṃ":"m","ṁ":"m","ḷ":"l"}
    for k,v in repl.items():
        s = s.replace(k,v)
    s = s.replace("ё","е")
    s = re.sub(r"[-–—\s_'’`.,!?():;«»\"/\\\\]", "", s)
    return s

def similar(a,b):
    a,b = normalize(a), normalize(b)
    if not a or not b: return False
    if a == b: return True
    if (a in b or b in a) and min(len(a), len(b)) >= 4: return True
    return SequenceMatcher(None, a, b).ratio() >= 0.88 and abs(len(a)-len(b)) <= 4

def visible_text(item, st, prefix):
    lang = st["lang"]
    ru = item.get(f"{prefix}_ru", "")
    en = item.get(f"{prefix}_en", "")
    iast = item.get(f"{prefix}_iast", "")
    if lang == "EN":
        return en or iast or ru
    if lang == "BOTH":
        parts = [x for x in [ru, en, iast] if x]
        return "\n".join(parts)
    parts = [ru] if ru else []
    if iast and item.get("show_iast_in_ru", False):
        parts.append(iast)
    return "\n".join(parts)

def q_text(q, st): return visible_text(q, st, "question")
def a_text(q, st): return visible_text(q, st, "answer")

def accepted_answers(q, st):
    ans = []
    if st["lang"] == "RU":
        for key in ["answer_ru", "answer_iast"]:
            if q.get(key): ans.append(q[key])
        ans += q.get("accepted_ru", [])
    elif st["lang"] == "EN":
        for key in ["answer_en", "answer_iast"]:
            if q.get(key): ans.append(q[key])
        ans += q.get("accepted_en", [])
    else:
        for key in ["answer_ru","answer_en","answer_iast"]:
            if q.get(key): ans.append(q[key])
        ans += q.get("accepted_ru", []) + q.get("accepted_en", [])
    ans += q.get("accepted_common", [])
    return [x for x in ans if x]

def filter_questions(st):
    qs = []
    for q in QUESTIONS:
        if q.get("level",1) > st["level"]:
            continue
        scope = q.get("language_scope", "any")
        if scope == "ru" and st["lang"] == "EN": continue
        if scope == "en" and st["lang"] == "RU": continue
        if scope == "both_only" and st["lang"] != "BOTH": continue
        if not q_text(q, st): continue
        qs.append(q)
    random.shuffle(qs)
    return qs

def filter_cards(st, limit=20):
    cards = [c for c in CARDS if q_text(c, st) and a_text(c, st)]
    random.shuffle(cards)
    return cards[:min(limit, len(cards))]

async def safe_menu(update, st, text=None):
    await update.message.reply_text(text or tx(st, "menu"), reply_markup=main_menu(st))

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = get_state(update.effective_user.id)
    st["mode"] = None; st["current"] = None
    await safe_menu(update, st, tx(st, "welcome"))

async def send_card(update, st):
    if not st["queue"]:
        st["mode"] = None; st["current"] = None
        await safe_menu(update, st, tx(st, "done_study"))
        return
    card = st["queue"].pop(0)
    st["current"] = card
    await update.message.reply_text(f"{tx(st,'card')}\n\n{q_text(card, st)}", reply_markup=study_menu(st))

async def reveal_card(update, st):
    card = st.get("current")
    if not card:
        await send_card(update, st)
        return
    await update.message.reply_text(f"{tx(st,'answer')}\n\n{a_text(card, st)}", reply_markup=study_menu(st))

async def send_test_q(update, st):
    if not st["queue"]:
        st["mode"] = None; st["current"] = None
        await safe_menu(update, st, f"{tx(st,'done_test')}\n\n{st['session_correct']}/{st['session_total']}")
        return
    q = st["queue"].pop(0)
    st["current"] = q
    if q.get("type") == "input":
        await update.message.reply_text(f"{tx(st,'test')}\n\n{q_text(q, st)}\n\n{tx(st,'write')}",
                                        reply_markup=ReplyKeyboardMarkup([[KeyboardButton("⬅️ Меню / Menu")]], resize_keyboard=True, one_time_keyboard=False))
    else:
        if st["lang"] == "RU":
            opts = q.get("options_ru", [])
        elif st["lang"] == "EN":
            opts = q.get("options_en", [])
        else:
            opts = q.get("options_both") or q.get("options_ru") or q.get("options_en") or []
        opts = opts[:]
        random.shuffle(opts)
        await update.message.reply_text(f"{tx(st,'test')}\n\n{q_text(q, st)}", reply_markup=answer_keyboard(opts))

async def handle_test_answer(update, st, s):
    q = st.get("current")
    if not q:
        await send_test_q(update, st)
        return
    ok = any(similar(s, ans) for ans in accepted_answers(q, st))
    st["total"] += 1; st["session_total"] += 1
    if ok:
        st["correct"] += 1; st["session_correct"] += 1; st["xp"] += 2
    prefix = tx(st, "right") if ok else tx(st, "wrong")
    await update.message.reply_text(f"{prefix}\n\n{tx(st,'answer')}\n{a_text(q, st)}")
    st["current"] = None
    await send_test_q(update, st)

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    st = get_state(update.effective_user.id)
    s = (update.message.text or "").strip()

    if menu_pressed(s):
        st["mode"] = None; st["current"] = None
        await safe_menu(update, st)
        return
    if study_pressed(s):
        st["mode"] = "study"; st["current"] = None; st["queue"] = filter_cards(st, 20)
        await update.message.reply_text(tx(st, "study_intro"), reply_markup=study_menu(st))
        await send_card(update, st)
        return
    if test_pressed(s):
        st["mode"] = "test"; st["current"] = None; st["session_correct"] = 0; st["session_total"] = 0
        st["queue"] = filter_questions(st)
        await update.message.reply_text(tx(st, "test_intro"), reply_markup=main_menu(st))
        await send_test_q(update, st)
        return
    if daily_pressed(s):
        st["mode"] = "study"; st["current"] = None; st["queue"] = filter_cards(st, 5)
        await send_card(update, st)
        return
    if progress_pressed(s):
        msg = f"📊 Progress / Прогресс\n\nXP: {st['xp']}\nCorrect: {st['correct']}\nTotal: {st['total']}\nLevel: {st['level']}\nScope: {st['scope']}"
        await update.message.reply_text(msg, reply_markup=main_menu(st))
        return
    if settings_pressed(s):
        st["mode"] = "settings"; st["current"] = None
        await update.message.reply_text(tx(st, "settings_text"), reply_markup=settings_menu())
        return

    if s == "🇷🇺 Русский":
        st["lang"] = "RU"
        await safe_menu(update, st, tx(st, "lang_ru"))
        return
    if s == "🇬🇧 English":
        st["lang"] = "EN"
        await safe_menu(update, st, tx(st, "lang_en"))
        return
    if s == "🌍 RU + EN":
        st["lang"] = "BOTH"
        await safe_menu(update, st, tx(st, "lang_both"))
        return
    if s == "Уровень 1":
        st["level"] = 1
        await safe_menu(update, st, f"{tx(st,'level_saved')} 1")
        return
    if s == "Уровень 2":
        st["level"] = 2
        await safe_menu(update, st, f"{tx(st,'level_saved')} 2")
        return
    if s == "📚 Выбор стихов / Verse scope":
        st["mode"] = "scope"; st["current"] = None
        await update.message.reply_text(tx(st, "scope_hint"), reply_markup=scope_menu())
        return
    if st.get("mode") == "scope":
        st["scope"] = s
        st["mode"] = None
        await safe_menu(update, st, f"{tx(st,'scope_saved')} {s}")
        return

    if st.get("mode") == "study":
        if card_response(s):
            await reveal_card(update, st)
            return
        if next_pressed(s):
            await send_card(update, st)
            return
        await update.message.reply_text(tx(st, "use_buttons"), reply_markup=study_menu(st))
        return

    if st.get("mode") == "test" and st.get("current"):
        await handle_test_answer(update, st, s)
        return

    await safe_menu(update, st, tx(st, "unknown"))

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE):
    print(f"ERROR: {context.error}")

def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing")
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("menu", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    app.add_error_handler(error_handler)
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
