from email.mime import message
import threading
import time
from telebot import types as telebot_types

from src.bot import bot
from src.config import (
    LATITUDE,
    LONGITUDE
)

from src.services.service_voice_agent import (
    procesar_audio_inline
)

from src.services.weather_service import (
    get_weather
)

from src.services.gemini_service import (
    consultar_capitales
)

from src.logger import logger

@bot.message_handler(content_types=['voice'])
def handle_voice(message):

    logger.info(f"Handler iniciado chat_id={message.chat.id}")

    threading.Thread(
        target=procesar_audio_inline,
        args=(message,),
        daemon=True
    ).start()

    logger.info(f"Thread lanzado")

@bot.message_handler(commands=['ping'])
def ping(message):

    inicio = time.time()

    bot.send_message(
        message.chat.id,
        "pong"
    )

    logger.info(
        f"send_message demoró {time.time()-inicio:.3f}s"
    )