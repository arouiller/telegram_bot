from flask import Flask
from flask import request

import telebot

from src.bot import bot
from src.config import TELEGRAM_TOKEN

import src.handlers.message_handlers
import src.handlers.callback_handlers

app = Flask(__name__)

@app.route(
    f"/{TELEGRAM_TOKEN}",
    methods=["POST"]
)
def webhook():
    json_string = (
        request.get_data()
        .decode("utf-8")
    )
    update = (
        telebot.types.Update
        .de_json(json_string)
    )
    bot.process_new_updates(
        [update]
    )
    return "ok", 200


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=5000
    )