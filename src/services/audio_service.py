import os
import requests

from src.bot import bot
from src.config import TELEGRAM_TOKEN
from src.services.gemini_service import transcribir_audio
from src.logger import logger

import tempfile
import requests

import time

def procesar_audio(message):
    logger.info("THREAD INICIADO")
    logger.info(f"Procesando mensaje de voz de {message.chat.id}")
    bot.send_chat_action(
        message.chat.id,
        "typing"
    )
    try:
        file_info = bot.get_file(
            message.voice.file_id
        )

        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{TELEGRAM_TOKEN}/"
            f"{file_info.file_path}"
        )

        logger.info("Inicio get_file")

        t0 = time.time()

        file_info = bot.get_file(
            message.voice.file_id
        )

        logger.info(
            f"Fin get_file ({time.time()-t0:.3f}s)"
        )

        logger.info(f"Inicio descarga del audio en la url {file_url}")

        inicio = time.time()

        response = requests.get(
            file_url,
            timeout=(5, 5)
        )

        logger.info(
            f"GET Telegram demoró {time.time()-inicio:.3f}s"
        )

        response.raise_for_status()
        logger.info(
            f"Tamaño audio: {len(response.content)} bytes"
        )
        logger.info(
            f"Status descarga: {response.status_code}"
        )

        with tempfile.NamedTemporaryFile(
            suffix=".ogg"
        ) as temp_audio:
            temp_audio.write(
                response.content
            )
            temp_audio.flush()
            logger.info(f"Iniciando transcripción del audio para {message.chat.id}")
            texto = transcribir_audio(
                temp_audio.name
            )
            logger.info(f"Transcripción completada para {message.chat.id}: {texto}")

        bot.send_message(
            message.chat.id,
            texto
        )

    except Exception as ex:

        bot.send_message(
            message.chat.id,
            f"Error: {str(ex)}"
        )
