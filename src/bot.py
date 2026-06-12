import telebot
from src.config import TELEGRAM_TOKEN

import src.handlers.message_handlers
import src.handlers.callback_handlers

bot = telebot.TeleBot(
    TELEGRAM_TOKEN,
    threaded=True
)