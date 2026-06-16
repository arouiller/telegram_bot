"""
Service Voice Agent - Procesa audios usando AgentOrchestrator.
Maneja transcripción, análisis de intención y procesamiento de gastos.
"""

from google import genai
from google.genai import types
import time
import requests

from src.config import GEMINI_API_KEY, LATITUDE, LONGITUDE, TELEGRAM_TOKEN
from src.logger import logger
from src.services.agent_orchestrator import orchestrator
from src.services.expense_service import (
    crear_gasto_pendiente,
    confirmar_gasto,
    cancelar_gasto,
    actualizar_categoria
)
from src.services.weather_service import get_weather
from src.services.conversation_state_service import (
    obtener_estado,
    ESTADO_IDLE,
    ESTADO_ESPERANDO_CONFIRMACION_GASTO
)

session = requests.Session()
client = genai.Client(api_key=GEMINI_API_KEY)


def get_clima_local() -> str:
    """Obtiene clima local."""
    return get_weather(
        latitud=LATITUDE,
        longitud=LONGITUDE
    )


def transcribir_audio(audio_bytes: bytes) -> str:
    """
    Transcribe audio usando el agente de voz.

    Args:
        audio_bytes: Bytes del archivo de audio

    Returns:
        Texto transcrito
    """
    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=[
                "Transcribe exactamente el audio. Devuelve únicamente la transcripción.",
                types.Part.from_bytes(
                    data=audio_bytes,
                    mime_type="audio/ogg"
                )
            ]
        )
        return response.text.strip()
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {str(e)}")
        raise


def procesar_estado_idle(texto: str, user_id: int) -> str:
    """
    Procesa texto en estado IDLE usando agente.
    Detecta si el usuario quiere registrar un gasto.

    Args:
        texto: Texto del usuario
        user_id: ID del usuario

    Returns:
        Respuesta del agente o confirmación de gasto
    """
    logger.info(f"🤖 Procesando estado IDLE con texto: {texto[:50]}... user_id={user_id}")

    try:
        prompt = f"""
Usuario dijo: {texto}

Analiza la intención del usuario.

Si desea registrar un gasto, devuelve exactamente:
GASTO|descripcion|monto

Ejemplo:
GASTO|Carrefour|15000

Para cualquier otra consulta responde de forma natural.
"""

        resultado = orchestrator.run_agent_sync("geography", prompt)
        resultado = resultado.strip()

        # Detectar si es un gasto
        if resultado.startswith("GASTO|"):
            try:
                partes = resultado.split("|")
                if len(partes) >= 3:
                    descripcion = partes[1]
                    monto = float(partes[2])

                    categoria = crear_gasto_pendiente(
                        user_id,
                        descripcion,
                        monto
                    )

                    logger.info(f"💰 Gasto detectado: {descripcion} ${monto:.2f}")

                    return (
                        f"💰 Detecté un gasto.\n\n"
                        f"Descripción: {descripcion}\n"
                        f"Monto: ${monto:.2f}\n"
                        f"Categoría sugerida: {categoria}\n\n"
                        f"¿Deseas registrarlo? (sí/no)"
                    )
            except (ValueError, IndexError) as e:
                logger.error(f"Error parseando gasto: {str(e)}")

        return resultado

    except Exception as e:
        logger.error(f"Error en procesar_estado_idle: {str(e)}")
        raise


def procesar_confirmacion_gasto(texto: str, user_id: int) -> str:
    """
    Procesa respuesta de confirmación de gasto.

    Args:
        texto: Respuesta del usuario
        user_id: ID del usuario

    Returns:
        Mensaje de confirmación o error
    """
    logger.info(f"💳 Procesando confirmación de gasto user_id={user_id}")

    try:
        prompt = f"""
Usuario respondió: {texto}

Clasifica únicamente como:
- CONFIRMAR
- CANCELAR
- CAMBIAR_CATEGORIA
- OTRO

Devuelve una sola palabra.
"""

        accion = orchestrator.run_agent_sync(
            "geography",
            prompt,
            temperature=0.1
        ).strip().upper()

        logger.info(f"Acción detectada: {accion}")

        if "CONFIRMAR" in accion:
            return confirmar_gasto(user_id)

        if "CANCELAR" in accion:
            return cancelar_gasto(user_id)

        # Intentar cambiar categoría
        categorias = [
            "Viveres", "Transporte", "Servicios", "Entretenimiento",
            "Tecnologia", "Salud", "Educacion", "Otros"
        ]

        texto_lower = texto.lower()
        for categoria in categorias:
            if categoria.lower() in texto_lower:
                actualizar_categoria(user_id, categoria)
                logger.info(f"Categoría actualizada a: {categoria}")

                return (
                    f"✅ Categoría actualizada a {categoria}.\n\n"
                    f"¿Deseas registrarlo? (sí/no)"
                )

        return (
            "❓ No entendí la respuesta.\n\n"
            "Puedes decir:\n"
            "✅ confirmar\n"
            "❌ cancelar\n"
            "📁 una categoría (Víveres, Transporte, etc.)"
        )

    except Exception as e:
        logger.error(f"Error en procesar_confirmacion_gasto: {str(e)}")
        raise


def procesar_audio_con_tools(audio_bytes: bytes, user_id: int) -> str:
    """
    Procesa audio considerando el estado del usuario.

    Args:
        audio_bytes: Bytes del audio
        user_id: ID del usuario

    Returns:
        Respuesta procesada
    """
    try:
        estado = obtener_estado(user_id)
        estado_actual = estado["estado"]

        logger.info(f"📊 Estado actual del usuario {user_id}: {estado_actual}")

        # Transcribir audio
        inicio = time.time()
        texto = transcribir_audio(audio_bytes)
        logger.info(f"⏱️ Transcripción completada en {time.time() - inicio:.3f}s")
        logger.info(f"📝 Texto: {texto[:100]}...")

        # Procesar según estado
        if estado_actual == ESTADO_IDLE:
            return procesar_estado_idle(texto, user_id)

        if estado_actual == ESTADO_ESPERANDO_CONFIRMACION_GASTO:
            return procesar_confirmacion_gasto(texto, user_id)

        return "❓ Estado desconocido. Intenta con /start"

    except Exception as e:
        logger.error(f"Error en procesar_audio_con_tools: {str(e)}")
        raise


def procesar_audio_inline(message):
    """
    Procesa mensaje de audio desde Telegram de forma asíncrona.

    Args:
        message: Objeto de mensaje de Telegram
    """
    chat_id = message.chat.id
    user_id = message.from_user.id
    file_id = message.voice.file_id

    logger.info(f"🎙️ [INLINE] Procesando audio chat_id={chat_id} user_id={user_id}")

    try:
        # ==========================================
        # GET FILE METADATA
        # ==========================================
        inicio = time.time()
        response = session.get(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/getFile",
            params={"file_id": file_id},
            timeout=(5, 5)
        )

        response.raise_for_status()
        data = response.json()

        if not data["ok"]:
            raise Exception(f"Error getFile: {data.get('description', 'Unknown')}")

        file_path = data["result"]["file_path"]
        logger.info(f"⏱️ getFile completado en {time.time() - inicio:.3f}s")

        # ==========================================
        # DOWNLOAD AUDIO
        # ==========================================
        file_url = f"https://api.telegram.org/file/bot{TELEGRAM_TOKEN}/{file_path}"

        inicio = time.time()
        response = session.get(file_url, timeout=(5, 5))
        response.raise_for_status()

        audio_bytes = response.content
        logger.info(
            f"⏱️ Descarga completada en {time.time() - inicio:.3f}s "
            f"({len(audio_bytes)} bytes)"
        )

        # ==========================================
        # PROCESS AUDIO
        # ==========================================
        inicio = time.time()
        resultado = procesar_audio_con_tools(audio_bytes, user_id)
        logger.info(f"⏱️ Procesamiento completado en {time.time() - inicio:.3f}s")

        # ==========================================
        # SEND RESPONSE
        # ==========================================
        inicio = time.time()
        response = session.post(
            f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
            data={"chat_id": chat_id, "text": resultado},
            timeout=(5, 5)
        )

        response.raise_for_status()
        logger.info(f"⏱️ Respuesta enviada en {time.time() - inicio:.3f}s")
        logger.info(f"✅ Audio procesado exitosamente")

    except Exception as ex:
        logger.exception("❌ Error procesando audio")

        try:
            session.post(
                f"https://api.telegram.org/bot{TELEGRAM_TOKEN}/sendMessage",
                data={
                    "chat_id": chat_id,
                    "text": f"❌ Error procesando audio: {str(ex)[:100]}"
                },
                timeout=(5, 5)
            )
        except Exception as e:
            logger.error(f"Error enviando mensaje de error: {str(e)}")