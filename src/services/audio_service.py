from src.logger import logger
import requests

from src.bot import bot
from src.config import TELEGRAM_TOKEN
from src.services.gemini_service import transcribir_audio

import tempfile
import requests

def procesar_audio(message):
    try:
        file_info = bot.get_file(
            message.voice.file_id
        )
        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{TELEGRAM_TOKEN}/"
            f"{file_info.file_path}"
        )
        logger.info("Inicio descarga de archivo de audio...")
        response = requests.get(
            file_url,
            timeout=30
        )
        response.raise_for_status()
        logger.info("Archivo de audio descargado.")

        with tempfile.NamedTemporaryFile(
            suffix=".ogg"
        ) as temp_audio:
            temp_audio.write(
                response.content
            )
            temp_audio.flush()
            logger.info("Archivo de audio guardado temporalmente. Iniciando transcripción...")
            texto = transcribir_audio(
                temp_audio.name
            )
            logger.info("Transcripción completada. Enviando mensaje al usuario.")

        bot.send_message(
            message.chat.id,
            texto
        )
        logger.info("Mensaje enviado al usuario.")

    except Exception as ex:

        bot.send_message(
            message.chat.id,
            f"Error: {str(ex)}"
        )
        logger.error(f"Error al procesar audio: {str(ex)}")
