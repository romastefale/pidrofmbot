import os
import re
import requests

from telegram import (
    Update,
    InlineQueryResultPhoto,
    InlineKeyboardMarkup,
    InlineKeyboardButton
)

from telegram.ext import (
    Application,
    InlineQueryHandler,
    MessageHandler,
    CallbackQueryHandler,
    ContextTypes,
    filters
)

TOKEN = os.getenv("TELEGRAM_TOKEN")

if not TOKEN:
    raise ValueError("Configure TELEGRAM_TOKEN nas variáveis do Render")


# =========================
# FUNÇÃO DE BUSCA
# =========================

def search_deezer(query, index=0):

    query = re.sub(r"[-_]+", " ", query)
    query = re.sub(r"\s+", " ", query).strip()

    r = requests.get(
        f"https://api.deezer.com/search?q={query}&index={index}",
        timeout=4
    )

    if r.status_code != 200:
        return []

    data = r.json()

    return data.get("data", [])


# =========================
# INLINE MODE (@bot musica)
# =========================

async def inline_query(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.inline_query.query

    if not query:
        return

    tracks = search_deezer(query)

    user = update.inline_query.from_user
    user_name = user.first_name if user else "Someone"

    results = []

    for i, track in enumerate(tracks[:10]):

        try:

            title = track["title"]
            artist = track["artist"]["name"]
            cover = track["album"]["cover_big"]

            results.append(

                InlineQueryResultPhoto(
                    id=str(i),
                    photo_url=cover,
                    thumbnail_url=cover,

                    title=f"{title} — {artist}",
                    description="Tap to share",

                    caption=f"_{user_name} is listening to..._\n\n♫ Playing: {title}\n★ Artist: {artist}",
                    parse_mode="Markdown"
                )
            )

        except:
            continue

    try:
        await update.inline_query.answer(results, cache_time=5)
    except:
        pass


# =========================
# BUSCA DIRETA NO CHAT
# =========================

async def search_music(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.message.text

    context.user_data["query"] = query
    context.user_data["offset"] = 0

    await send_results(update, context)


# =========================
# ENVIA RESULTADOS
# =========================

async def send_results(update, context):

    query = context.user_data["query"]
    offset = context.user_data["offset"]

    tracks = search_deezer(query, offset)

    if not tracks:
        await update.message.reply_text("No results found.")
        return

    context.user_data["tracks"] = tracks

    keyboard = []

    for i, track in enumerate(tracks[:10]):

        title = track["title"]
        artist = track["artist"]["name"]

        keyboard.append([
            InlineKeyboardButton(
                f"{title} — {artist}",
                callback_data=f"track_{i}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "Load more",
            callback_data="more"
        )
    ])

    reply_markup = InlineKeyboardMarkup(keyboard)

    await update.message.reply_text(
        "Select the song:",
        reply_markup=reply_markup
    )


# =========================
# LOAD MORE
# =========================

async def more_results(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    context.user_data["offset"] += 10

    await query.answer()

    tracks = search_deezer(
        context.user_data["query"],
        context.user_data["offset"]
    )

    if not tracks:
        await query.message.reply_text("No more results.")
        return

    context.user_data["tracks"] = tracks

    keyboard = []

    for i, track in enumerate(tracks[:10]):

        title = track["title"]
        artist = track["artist"]["name"]

        keyboard.append([
            InlineKeyboardButton(
                f"{title} — {artist}",
                callback_data=f"track_{i}"
            )
        ])

    keyboard.append([
        InlineKeyboardButton(
            "Load more",
            callback_data="more"
        )
    ])

    await query.message.reply_text(
        "More results:",
        reply_markup=InlineKeyboardMarkup(keyboard)
    )


# =========================
# SELECIONAR MÚSICA
# =========================

async def select_track(update: Update, context: ContextTypes.DEFAULT_TYPE):

    query = update.callback_query

    index = int(query.data.split("_")[1])

    tracks = context.user_data.get("tracks")

    if not tracks:
        return

    track = tracks[index]

    title = track["title"]
    artist = track["artist"]["name"]
    cover = track["album"]["cover_big"]

    user_name = query.from_user.first_name

    await query.message.reply_photo(
        photo=cover,
        caption=f"_{user_name} is listening to..._\n\n♫ Playing: {title}\n★ Artist: {artist}",
        parse_mode="Markdown"
    )

    await query.answer()


# =========================
# MAIN
# =========================

def main():

    app = Application.builder().token(TOKEN).build()

    app.add_handler(InlineQueryHandler(inline_query))

    app.add_handler(
        MessageHandler(filters.TEXT & ~filters.COMMAND, search_music)
    )

    app.add_handler(
        CallbackQueryHandler(more_results, pattern="more")
    )

    app.add_handler(
        CallbackQueryHandler(select_track, pattern="track_")
    )

    print("Bot rodando...")

    app.run_polling()


if __name__ == "__main__":
    main()
