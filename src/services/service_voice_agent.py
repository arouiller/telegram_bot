"""
Service Voice Agent - Procesa audios usando AgentOrchestrator.
Maneja transcripción, análisis de intención y procesamiento de gastos.
"""

import time
import requests

from src.config import TELEGRAM_TOKEN
from src.logger import logger
from src.services.agent_orchestrator import orchestrator
from src.services.conversation_state_service import (
    obtener_estado,
    ESTADO_IDLE,
    ESTADO_REGISTRANDO_GASTO,
    ESTADO_ESPERANDO_CONFIRMACION_GASTO
)

session = requests.Session()


def procesar_gasto(texto: str, user_id: int) -> str:
    """
    Procesa un audio identificado como gasto usando el agente conversacional.

    El agente maneja todo el ciclo de vida del gasto:
    - Crear gasto latente
    - Extraer información del audio
    - Actualizar campos
    - Mostrar estado
    - Pedir información faltante

    Args:
        texto: Texto del usuario con información de gasto
        user_id: ID del usuario

    Returns:
        Respuesta del agente con estado y próximos pasos
    """
    logger.info(f"💰 Procesando gasto desde audio (con agente): {texto[:50]}...")

    try:
        prompt = f"""
User ID: {user_id}
Texto del usuario: {texto}

Procesa esta información de gasto conversacionalmente.
Si el usuario menciona información de gasto (monto, descripción, medio de pago, etc),
extrae y actualiza el gasto latente.
Muestra el estado actual y qué está pendiente.
"""
        resultado = orchestrator.run_agent_sync("expense", prompt)
        return resultado.strip()

    except Exception as e:
        logger.error(f"Error en procesar_gasto: {str(e)}")
        return "❌ Error procesando gasto. Intenta nuevamente."

def procesar_clima(texto: str) -> str:
    """
    Procesa una consulta de clima usando el agente especializado.

    Args:
        texto: Pregunta sobre clima del usuario

    Returns:
        Respuesta sobre clima
    """
    logger.info(f"🌤️ Procesando clima desde audio: {texto[:50]}...")

    try:
        prompt = f"""
Usuario pregunta: {texto}

Responde la pregunta sobre clima.
"""
        resultado = orchestrator.run_agent_sync("weather", prompt)
        return resultado.strip()

    except Exception as e:
        logger.error(f"Error en procesar_clima: {str(e)}")
        raise


def procesar_geografia(texto: str) -> str:
    """
    Procesa una consulta de geografía usando el agente especializado.

    Args:
        texto: Pregunta sobre geografía del usuario

    Returns:
        Respuesta sobre geografía
    """
    logger.info(f"📍 Procesando geografía desde audio: {texto[:50]}...")

    try:
        prompt = f"""
Usuario pregunta: {texto}

Responde la pregunta sobre geografía.
"""
        resultado = orchestrator.run_agent_sync("geography", prompt)
        return resultado.strip()

    except Exception as e:
        logger.error(f"Error en procesar_geografia: {str(e)}")
        raise


def procesar_estado_idle(texto: str, user_id: int) -> str:
    """
    Procesa texto en estado IDLE detectando la intención del usuario.

    Detecta automáticamente si es:
    - Gasto: registrar gastos
    - Clima: consulta sobre clima/temperatura
    - Geografía: consulta sobre capitales/países
    - Otro: cualquier otra consulta

    Args:
        texto: Texto del usuario
        user_id: ID del usuario

    Returns:
        Respuesta apropiada según la intención detectada
    """
    logger.info(f"🤖 Procesando estado IDLE: {texto[:50]}... user_id={user_id}")

    try:
        intencion = orchestrator.detect_intention_sync(texto)
        logger.info(f"📊 Intención detectada: {intencion}")

        if intencion == "GASTO":
            logger.info(f"💰 Procesando como GASTO")
            return procesar_gasto(texto, user_id)

        elif intencion == "CLIMA":
            logger.info(f"🌤️ Procesando como CLIMA")
            try:
                return procesar_clima(texto)
            except Exception as e:
                logger.error(f"Error obteniendo clima: {str(e)}")
                return "No pude obtener la información climática en este momento."

        elif intencion == "GEOGRAFIA":
            logger.info(f"📍 Procesando como GEOGRAFIA")
            return procesar_geografia(texto)

        else:  # intencion == "OTRO"
            logger.info(f"❓ Procesando como OTRA consulta")
            return (
                "No estoy seguro de tu pregunta. Puedo ayudarte con:\n"
                "🌤️ Clima (temperatura, lluvia, etc)\n"
                "📍 Geografía (capitales, países, etc)\n"
                "💰 Registrar gastos\n\n"
                "¿Qué necesitas?"
            )

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
        # Obtener la medatada del archivo de audio
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
        # Descargar el archivo de audio usando file_path
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
        # transcribir el audio a texto
        # ==========================================
        inicio = time.time()

        # Obtener estado actual del usuario
        estado = obtener_estado(user_id)
        estado_actual = estado["estado"]
        logger.info(f"📊 Estado actual del usuario {user_id}: {estado_actual}")

        # Transcribir el audio a texto
        transcripcion_inicio = time.time()
        texto = orchestrator.transcribe_audio_sync(audio_bytes)
        logger.info(f"⏱️ Transcripción completada en {time.time() - transcripcion_inicio:.3f}s")
        logger.info(f"📝 Texto: {texto[:100]}...")

        # ==========================================
        # Procesar según estado
        # ==========================================
        if estado_actual == ESTADO_IDLE:
            resultado = procesar_estado_idle(texto, user_id)
        elif estado_actual == ESTADO_REGISTRANDO_GASTO:
            # En estado de registro de gasto, el agente continúa el diálogo
            logger.info(f"💰 Continuando registro de gasto")
            resultado = procesar_gasto(texto, user_id)
        elif estado_actual == ESTADO_ESPERANDO_CONFIRMACION_GASTO:
            resultado = procesar_confirmacion_gasto(texto, user_id)
        else:
            resultado = "❓ Estado desconocido. Intenta con /start"

        logger.info(f"⏱️ Procesamiento completado en {time.time() - inicio:.3f}s")

        # ==========================================
        # Responder al usuario con el resultado
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