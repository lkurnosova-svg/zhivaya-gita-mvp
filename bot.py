
import json
import os
import random
import re
from pathlib import Path
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ContextTypes,
    filters,
)

BOT_TOKEN = os.getenv("BOT_TOKEN")

BASE = Path(__file__).resolve().parent

with open(BASE / "bg_chapter1_questions_full.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f)["questions"]

USER = {}

def normalize(text):
    text = text.lower()
    text = re.sub(r"[-–—\\s]", "", text)
    text = re.sub(r"[.,!?()]", "", text)
    replacements = {
        "ṣ":"s","ś":"s","ā":"a","ī":"i","ū":"u","ṛ":"r","ṅ":"n","ñ":"n","ṭ":"t","ḍ":"d","ḥ":"h","ṃ":"m","ç":"c"
    }
    for k,v in replacements.items():
        text = text.replace(k,v)
    return text

def main_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📖 Изучение"), KeyboardButton("🧠 Тест")],
        [KeyboardButton("🔥 Daily Practice"), KeyboardButton("📊 Прогресс")],
        [KeyboardButton("⚙ Настройки")]
    ], resize_keyboard=True)

def study_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("10 карточек"), KeyboardButton("20 карточек")],
        [KeyboardButton("⬅️ Меню")]
    ], resize_keyboard=True)

def settings_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("🇷🇺 Русский"), KeyboardButton("🇬🇧 English")],
        [KeyboardButton("🌍 RU + EN")],
        [KeyboardButton("📚 Выбор стихов")],
        [KeyboardButton("⬅️ Меню")]
    ], resize_keyboard=True)

def card_buttons():
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Знаю"), KeyboardButton("🤔 Затрудняюсь")],
        [KeyboardButton("❌ Не знаю")],
        [KeyboardButton("➡️ Следующая карточка")],
        [KeyboardButton("⬅️ Меню")]
    ], resize_keyboard=True)

def verse_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("1.1"), KeyboardButton("1.1–1.5")],
        [KeyboardButton("Глава 1"), KeyboardButton("Вся Гита")],
        [KeyboardButton("⬅️ Меню")]
    ], resize_keyboard=True)

def answer_buttons(options):
    rows = [[KeyboardButton(x)] for x in options]
    rows.append([KeyboardButton("⬅️ Меню")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def get_lang_question(q, lang):
    if lang == "EN":
        return q.get("question_en", q["question_ru"])
    if lang == "BOTH":
        return f"{q['question_ru']}\\n\\n{q.get('question_en','')}"
    return q["question_ru"]

def get_lang_answers(q):
    return q.get("accepted_answers", [q["answer_ru"]])

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id

    USER.setdefault(uid, {
        "xp":0,
        "correct":0,
        "total":0,
        "lang":"RU",
        "study_size":20,
        "mode":None,
        "queue":[],
        "current":None
    })

    await update.message.reply_text(
        "🌿 Живая Гита\\n\\nПолноценный MVP первой главы.",
        reply_markup=main_menu()
    )

async def send_study_card(update, uid):
    state = USER[uid]

    if not state["queue"]:
        await update.message.reply_text(
            "✅ Сессия изучения завершена",
            reply_markup=main_menu()
        )
        return

    q = state["queue"].pop(0)
    state["current"] = q

    await update.message.reply_text(
        "🃏 Карточка\\n\\n" + get_lang_question(q, state["lang"]),
        reply_markup=card_buttons()
    )

async def reveal_card(update, uid):
    q = USER[uid]["current"]

    text = (
        "✅ Правильный ответ:\\n\\n"
        + q["answer_ru"]
    )

    if q.get("answer_en"):
        text += "\\n" + q["answer_en"]

    if q.get("answer_iast"):
        text += "\\n" + q["answer_iast"]

    await update.message.reply_text(text, reply_markup=card_buttons())

async def send_test_question(update, uid):
    state = USER[uid]

    if not state["queue"]:
        await update.message.reply_text(
            f"🏁 Тест завершён\\n\\n"
            f"Правильных: {state['session_correct']}/{state['session_total']}",
            reply_markup=main_menu()
        )
        return

    q = state["queue"].pop(0)
    state["current"] = q

    qtype = q.get("type","choice")

    if qtype == "choice":
        opts = q["options"][:]
        random.shuffle(opts)

        await update.message.reply_text(
            "🧠 Тест\\n\\n" + get_lang_question(q, state["lang"]),
            reply_markup=answer_buttons(opts)
        )
    else:
        await update.message.reply_text(
            "🧠 Тест\\n\\n"
            + get_lang_question(q, state["lang"])
            + "\\n\\n✍️ Напиши ответ",
            reply_markup=ReplyKeyboardMarkup([
                [KeyboardButton("⬅️ Меню")]
            ], resize_keyboard=True)
        )

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    USER.setdefault(uid,{
        "xp":0,
        "correct":0,
        "total":0,
        "lang":"RU",
        "study_size":20,
        "mode":None,
        "queue":[],
        "current":None
    })

    state = USER[uid]
    txt = update.message.text

    if txt == "⬅️ Меню":
        await update.message.reply_text("Главное меню", reply_markup=main_menu())
        return

    if txt == "📖 Изучение":
        state["mode"] = "study"
        await update.message.reply_text(
            "Выберите количество карточек",
            reply_markup=study_menu()
        )
        return

    if txt in ["10 карточек","20 карточек"]:
        size = 10 if "10" in txt else 20
        state["study_size"] = size
        state["queue"] = random.sample(QUESTIONS, min(size, len(QUESTIONS)))
        await send_study_card(update, uid)
        return

    if txt in ["✅ Знаю","🤔 Затрудняюсь","❌ Не знаю"]:
        await reveal_card(update, uid)
        return

    if txt == "➡️ Следующая карточка":
        await send_study_card(update, uid)
        return

    if txt == "🧠 Тест":
        state["mode"] = "test"
        state["queue"] = QUESTIONS[:]
        random.shuffle(state["queue"])
        state["session_correct"] = 0
        state["session_total"] = 0
        await send_test_question(update, uid)
        return

    if txt == "📊 Прогресс":
        await update.message.reply_text(
            f"📊 Прогресс\\n\\n"
            f"XP: {state['xp']}\\n"
            f"Правильных ответов: {state['correct']}\\n"
            f"Всего ответов: {state['total']}"
        )
        return

    if txt == "🔥 Daily Practice":
        state["queue"] = random.sample(QUESTIONS, min(5, len(QUESTIONS)))
        await send_study_card(update, uid)
        return

    if txt == "⚙ Настройки":
        await update.message.reply_text(
            "⚙ Настройки",
            reply_markup=settings_menu()
        )
        return

    if txt == "🇷🇺 Русский":
        state["lang"] = "RU"
        await update.message.reply_text("Язык переключён: Русский")
        return

    if txt == "🇬🇧 English":
        state["lang"] = "EN"
        await update.message.reply_text("Language switched: English")
        return

    if txt == "🌍 RU + EN":
        state["lang"] = "BOTH"
        await update.message.reply_text("Режим: RU + EN")
        return

    if txt == "📚 Выбор стихов":
        await update.message.reply_text(
            "Введите диапазон\\nнапример: 1.1, 1.1–1.5, Глава 1",
            reply_markup=verse_menu()
        )
        return

    current = state.get("current")

    if current:
        state["total"] += 1
        state["session_total"] += 1

        answers = [normalize(x) for x in get_lang_answers(current)]

        if normalize(txt) in answers:
            state["correct"] += 1
            state["session_correct"] += 1
            state["xp"] += 2

            await update.message.reply_text(
                "✅ Верно\\n\\nПравильный ответ:\\n" + current["answer_ru"]
            )
        else:
            await update.message.reply_text(
                "❌ Неверно\\n\\nПравильный ответ:\\n" + current["answer_ru"]
            )

        state["current"] = None
        await send_test_question(update, uid)

app = Application.builder().token(BOT_TOKEN).build()

app.add_handler(CommandHandler("start", start))
app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

app.run_polling()
