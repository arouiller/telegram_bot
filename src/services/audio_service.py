import tempfile
import time
import requests

from src.config import TELEGRAM_TOKEN
from src.services.gemini_service import transcribir_audio
from src.services.gemini_service import transcribir_audio_bytes
from src.logger import logger
from src.services.service_voice_agent import (
    procesar_audio_con_tools
)


session = requests.Session()


def procesar_audio(message):

    chat_id = message.chat.id
    file_id = message.voice.file_id

    logger.info(
        f"Procesando audio. chat_id={chat_id} file_id={file_id}"
    )

    try:

        # ==========================================
        # GET FILE
        # ==========================================

        inicio = time.time()

        response = session.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
            params={
                "file_id": file_id
            },
            timeout=(5, 5)
        )

        logger.info(
            f"getFile demoró {time.time() - inicio:.3f}s"
        )

        response.raise_for_status()

        data = response.json()

        if not data["ok"]:
            raise Exception(
                f"Error getFile: {data}"
            )

        file_path = data["result"]["file_path"]

        # ==========================================
        # DESCARGA AUDIO
        # ==========================================

        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{TELEGRAM_TOKEN}/"
            f"{file_path}"
        )

        inicio = time.time()

        response = session.get(
            file_url,
            timeout=(5, 5)
        )

        logger.info(
            f"Descarga audio demoró "
            f"{time.time() - inicio:.3f}s"
        )

        response.raise_for_status()

        logger.info(
            f"Tamaño audio: {len(response.content)} bytes"
        )

        # ==========================================
        # TRANSCRIPCION
        # ==========================================

        with tempfile.NamedTemporaryFile(
            suffix=".ogg"
        ) as temp_audio:

            temp_audio.write(
                response.content
            )

            temp_audio.flush()

            inicio = time.time()

            texto = transcribir_audio(
                temp_audio.name
            )

            logger.info(
                f"Gemini demoró "
                f"{time.time() - inicio:.3f}s"
            )

        logger.info(
            f"Texto obtenido: {texto}"
        )

        # ==========================================
        # SEND MESSAGE
        # ==========================================

        inicio = time.time()

        response = session.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": texto
            },
            timeout=(5, 5)
        )

        logger.info(
            f"sendMessage demoró "
            f"{time.time() - inicio:.3f}s"
        )

        response.raise_for_status()

    except Exception as ex:

        logger.exception(
            "Error procesando audio"
        )

        try:
            session.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": f"Error: {str(ex)}"
                },
                timeout=(5, 5)
            )
        except Exception:
            pass

def procesar_audio_inline(message):

    chat_id = message.chat.id
    file_id = message.voice.file_id

    logger.info(
        f"[INLINE] Procesando audio. chat_id={chat_id} file_id={file_id}"
    )

    try:

        # ==========================================
        # GET FILE
        # ==========================================

        inicio = time.time()

        response = session.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
            params={
                "file_id": file_id
            },
            timeout=(5, 5)
        )

        logger.info(
            f"[INLINE] getFile demoró "
            f"{time.time() - inicio:.3f}s"
        )

        response.raise_for_status()

        data = response.json()

        if not data["ok"]:
            raise Exception(
                f"Error getFile: {data}"
            )

        file_path = data["result"]["file_path"]

        # ==========================================
        # DESCARGA AUDIO
        # ==========================================

        file_url = (
            f"https://api.telegram.org/file/bot"
            f"{TELEGRAM_TOKEN}/"
            f"{file_path}"
        )

        inicio = time.time()

        response = session.get(
            file_url,
            timeout=(5, 5)
        )

        logger.info(
            f"[INLINE] Descarga audio demoró "
            f"{time.time() - inicio:.3f}s"
        )

        response.raise_for_status()

        audio_bytes = response.content

        logger.info(
            f"[INLINE] Tamaño audio: "
            f"{len(audio_bytes)} bytes"
        )

        # ==========================================
        # TRANSCRIPCIÓN DIRECTA
        # ==========================================

        inicio = time.time()

        texto = procesar_audio_con_tools(
            audio_bytes, message.chat.id
        )

        logger.info(
            f"[INLINE] Gemini demoró "
            f"{time.time() - inicio:.3f}s"
        )

        logger.info(
            f"[INLINE] Texto obtenido: {texto}"
        )

        # ==========================================
        # SEND MESSAGE
        # ==========================================

        inicio = time.time()

        response = session.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={
                "chat_id": chat_id,
                "text": texto
            },
            timeout=(5, 5)
        )

        logger.info(
            f"[INLINE] sendMessage demoró "
            f"{time.time() - inicio:.3f}s"
        )

        response.raise_for_status()

    except Exception as ex:

        logger.exception(
            "[INLINE] Error procesando audio"
        )

        try:
            session.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": f"Error: {str(ex)}"
                },
                timeout=(5, 5)
            )
        except Exception:
            pass