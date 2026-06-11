import threading

from telebot import types as telebot_types

from src.bot import bot
from src.config import (
    LATITUDE,
    LONGITUDE
)

from src.services.audio_service import (
    procesar_audio
)

from src.services.weather_service import (
    get_weather
)

from src.services.gemini_service import (
    consultar_capitales
)

from src.logger import logger

@bot.message_handler(
    content_types=['voice']
)
def handle_voice(message):
    logger.info(
        f"HANDLE VOICE {message.voice.file_id}"
    )    
    bot.reply_to(
        message,
        "🎙️ Audio recibido. Transcribiendo..."
    )

    threading.Thread(
        target=procesar_audio,
        args=(message,),
        daemon=True
    ).start()

@bot.message_handler(
    func=lambda m:
    m.text and m.text.lower() == "clima"
)
def send_weather(message):
    bot.reply_to(
        message,
        get_weather(
            LATITUDE,
            LONGITUDE
        )
    )

@bot.message_handler(
    func=lambda m:
    m.text and m.text.lower() == "gemini"
)
def send_capital(message):
    bot.reply_to(
        message,
        consultar_capitales(
            "ARGENTINA"
        )
    )