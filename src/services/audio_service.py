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

        response = requests.get(
            file_url,
            timeout=30
        )
        response.raise_for_status()

        with tempfile.NamedTemporaryFile(
            suffix=".ogg"
        ) as temp_audio:
            temp_audio.write(
                response.content
            )
            temp_audio.flush()
            texto = transcribir_audio(
                temp_audio.name
            )

        bot.send_message(
            message.chat.id,
            texto
        )

    except Exception as ex:

        bot.send_message(
            message.chat.id,
            f"Error: {str(ex)}"
        )
