
import json
import os
import random
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

with open(BASE / "bg_chapter1_test_questions_mvp.json", "r", encoding="utf-8") as f:
    QUESTIONS = json.load(f).get("questions", [])

USER = {}

def menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("📖 Изучение"), KeyboardButton("🧠 Тест")],
        [KeyboardButton("🃏 Карточки"), KeyboardButton("📊 Прогресс")],
        [KeyboardButton("🔥 Daily"), KeyboardButton("⚙ Настройки")]
    ], resize_keyboard=True)

def level_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("Level 1")],
        [KeyboardButton("Level 2")],
        [KeyboardButton("⬅️ Меню")]
    ], resize_keyboard=True)

def answer_menu(opts):
    rows = [[KeyboardButton(x)] for x in opts]
    rows.append([KeyboardButton("➡️ Далее")])
    rows.append([KeyboardButton("⬅️ Меню")])
    return ReplyKeyboardMarkup(rows, resize_keyboard=True)

def flash_menu():
    return ReplyKeyboardMarkup([
        [KeyboardButton("✅ Знаю"), KeyboardButton("⚠️ Сложно")],
        [KeyboardButton("🔁 Повторить"), KeyboardButton("⬅️ Меню")]
    ], resize_keyboard=True)

def get_questions(level):
    if level == 1:
        out = [q for q in QUESTIONS if q.get("is_key_verse")]
        return out if out else QUESTIONS
    return QUESTIONS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    USER.setdefault(uid, {
        "xp": 0,
        "correct": 0,
        "total": 0,
        "streak": 0,
        "hard": [],
        "favorites": []
    })

    text = (
        "🌿 Живая Гита\n\n"
        "MVP первой главы.\n\n"
        "Доступно:\n"
        "• тесты\n"
        "• карточки\n"
        "• XP\n"
        "• сложные вопросы\n"
        "• Daily practice\n"
        "• прогресс\n"
    )

    await update.message.reply_text(text, reply_markup=menu())

async def send_question(update, uid):
    state = USER[uid]

    if not state["queue"]:
        await update.message.reply_text(
            f"✅ Тест завершён\n\n"
            f"Правильных: {state['session_correct']}/{state['session_total']}\n"
            f"XP: {state['xp']}",
            reply_markup=menu()
        )
        return

    q = state["queue"].pop(0)
    state["current"] = q

    opts = q.get("options", [])

    correct = q.get("answer_ru")
    if correct and correct not in opts:
        opts.append(correct)

    random.shuffle(opts)

    await update.message.reply_text(
        q.get("question_ru", "Вопрос"),
        reply_markup=answer_menu(opts)
    )

async def show_card(update, uid):
    q = random.choice(QUESTIONS)
    USER[uid]["card"] = q

    text = (
        f"🃏 Карточка\n\n"
        f"{q.get('question_ru','')}\n\n"
        f"Ответ:\n{q.get('answer_ru','')}"
    )

    await update.message.reply_text(text, reply_markup=flash_menu())

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    USER.setdefault(uid, {
        "xp": 0,
        "correct": 0,
        "total": 0,
        "streak": 0,
        "hard": [],
        "favorites": []
    })

    txt = update.message.text
    state = USER[uid]

    if txt == "⬅️ Меню":
        await update.message.reply_text("Главное меню", reply_markup=menu())
        return

    if txt == "📖 Изучение":
        await update.message.reply_text(
            "Выберите уровень",
            reply_markup=level_menu()
        )
        return

    if txt == "🧠 Тест":
        await update.message.reply_text(
            "Выберите уровень теста",
            reply_markup=level_menu()
        )
        return

    if txt == "Level 1":
        state["queue"] = get_questions(1)[:5]
        random.shuffle(state["queue"])
        state["session_correct"] = 0
        state["session_total"] = 0
        await send_question(update, uid)
        return

    if txt == "Level 2":
        state["queue"] = get_questions(2)[:15]
        random.shuffle(state["queue"])
        state["session_correct"] = 0
        state["session_total"] = 0
        await send_question(update, uid)
        return

    if txt == "➡️ Далее":
        await send_question(update, uid)
        return

    if txt == "🃏 Карточки":
        await show_card(update, uid)
        return

    if txt == "📊 Прогресс":
        await update.message.reply_text(
            f"📊 Прогресс\n\n"
            f"XP: {state['xp']}\n"
            f"Правильных ответов: {state['correct']}\n"
            f"Всего ответов: {state['total']}\n"
            f"Сложных вопросов: {len(state['hard'])}\n"
            f"Streak: {state['streak']}"
        )
        return

    if txt == "🔥 Daily":
        state["streak"] += 1
        q = random.choice(get_questions(1))
        await update.message.reply_text(
            f"🔥 Daily practice\n\n"
            f"{q.get('question_ru','')}\n\n"
            f"Ответ:\n{q.get('answer_ru','')}",
            reply_markup=flash_menu()
        )
        return

    if txt == "⚙ Настройки":
        await update.message.reply_text(
            "Настройки MVP\n\n"
            "• RU включён\n"
            "• Level 1/2 активны\n"
            "• Daily active\n"
            "• XP active",
            reply_markup=menu()
        )
        return

    if txt in ["✅ Знаю", "⚠️ Сложно", "🔁 Повторить"]:
        if txt == "✅ Знаю":
            state["xp"] += 1
        elif txt == "⚠️ Сложно":
            card = state.get("card")
            if card:
                state["hard"].append(card)
        await show_card(update, uid)
        return

    current = state.get("current")

    if current:
        state["total"] += 1
        state["session_total"] += 1

        correct = current.get("answer_ru","").strip().lower()

        if txt.strip().lower() == correct:
            state["correct"] += 1
            state["session_correct"] += 1
            state["xp"] += 2
            await update.message.reply_text("✅ Правильно")
        else:
            await update.message.reply_text(
                f"❌ Неправильно\n\nПравильный ответ:\n{current.get('answer_ru','')}"
            )

        state["current"] = None
        await send_question(update, uid)
        return

    await update.message.reply_text(
        "Нажмите /start",
        reply_markup=menu()
    )

def main():
    app = Application.builder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))

    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
