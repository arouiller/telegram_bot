"""
Service Voice Agent - Procesa audios usando AgentOrchestrator.
Maneja transcripción, análisis de intención y procesamiento de gastos.
"""

import time
import requests

from src.config import TELEGRAM_TOKEN
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

# Palabras clave para detección de intención
PALABRAS_CLAVE_GASTO = [
    "registrar", "gasto", "pagar", "gasté", "pagué",
    "salida", "cuenta", "factura", "costo", "egreso"
]

PALABRAS_CLAVE_CLIMA = [
    "clima", "temperatura", "lluvia", "tiempo",
    "frío", "calor", "soleado", "nublado", "cielo",
    "nubes", "viento", "humedad", "llueve", "lluvia"
]

PALABRAS_CLAVE_GEOGRAFIA = [
    "capital", "país", "pais", "ciudad", "ubicación",
    "donde", "dónde", "capital de", "geografía", "geografia"
]


def detectar_intension(texto: str) -> str:
    """
    Detecta la intención del usuario basado en palabras clave.

    Args:
        texto: Texto del usuario

    Returns:
        "GASTO" si es sobre registrar gastos
        "CLIMA" si es sobre clima/temperatura
        "GEOGRAFIA" si es sobre geografía
        "OTRO" para cualquier otra consulta
    """
    texto_lower = texto.lower()

    if any(palabra in texto_lower for palabra in PALABRAS_CLAVE_GASTO):
        return "GASTO"

    if any(palabra in texto_lower for palabra in PALABRAS_CLAVE_CLIMA):
        return "CLIMA"

    if any(palabra in texto_lower for palabra in PALABRAS_CLAVE_GEOGRAFIA):
        return "GEOGRAFIA"

    return "OTRO"


def transcribir_audio(audio_bytes: bytes) -> str:
    """
    Transcribe audio usando el agente de transcripción del orquestador.

    Args:
        audio_bytes: Bytes del archivo de audio

    Returns:
        Texto transcrito
    """
    try:
        return orchestrator.transcribe_audio_sync(audio_bytes)
    except Exception as e:
        logger.error(f"Error transcribiendo audio: {str(e)}")
        raise


def procesar_gasto_desde_audio(texto: str, user_id: int) -> str:
    """
    Procesa un audio identificado como gasto.

    Args:
        texto: Texto del usuario con información de gasto
        user_id: ID del usuario

    Returns:
        Confirmación de gasto creado o mensaje de error
    """
    logger.info(f"💰 Procesando gasto desde audio: {texto[:50]}...")

    try:
        prompt = f"""
Usuario dijo: {texto}

Extrae información de gasto. Si menciona un gasto, devuelve exactamente:
GASTO|descripcion|monto

Ejemplo:
GASTO|Carrefour|15000

Si no hay información clara de gasto, devuelve:
NO_GASTO

Sé conciso en la descripción.
"""

        resultado = orchestrator.run_agent_sync("geography", prompt)
        resultado = resultado.strip()

        if resultado.startswith("GASTO|"):
            try:
                partes = resultado.split("|")
                if len(partes) >= 3:
                    descripcion = partes[1].strip()
                    monto = float(partes[2].strip())

                    categoria = crear_gasto_pendiente(
                        user_id,
                        descripcion,
                        monto
                    )

                    logger.info(f"💰 Gasto creado: {descripcion} ${monto:.2f}")

                    return (
                        f"💰 Detecté un gasto.\n\n"
                        f"Descripción: {descripcion}\n"
                        f"Monto: ${monto:.2f}\n"
                        f"Categoría sugerida: {categoria}\n\n"
                        f"¿Deseas registrarlo? (sí/no)"
                    )
            except (ValueError, IndexError) as e:
                logger.error(f"Error parseando gasto: {str(e)}")
                return "No pude procesar la información del gasto. ¿Puedes repetir?"

        return "No detecté información clara de gasto. ¿Podrías ser más específico?"

    except Exception as e:
        logger.error(f"Error en procesar_gasto_desde_audio: {str(e)}")
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
        intension = detectar_intension(texto)
        logger.info(f"📊 Intención detectada: {intension}")

        if intension == "GASTO":
            logger.info(f"💰 Procesando como GASTO")
            return procesar_gasto_desde_audio(texto, user_id)

        elif intension == "CLIMA":
            logger.info(f"🌤️ Procesando como CLIMA")
            try:
                return get_weather()
            except Exception as e:
                logger.error(f"Error obteniendo clima: {str(e)}")
                return "No pude obtener la información climática en este momento."

        elif intension == "GEOGRAFIA":
            logger.info(f"📍 Procesando como GEOGRAFIA")
            prompt = f"""
Usuario pregunta: {texto}

Responde la pregunta sobre geografía.
"""
            resultado = orchestrator.run_agent_sync("geography", prompt)
            return resultado.strip()

        else:  # intension == "OTRO"
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
        # ==========================================================
        # Obtener estado actual del usuario
        # ==========================================================
        estado = obtener_estado(user_id)
        estado_actual = estado["estado"]

        logger.info(f"📊 Estado actual del usuario {user_id}: {estado_actual}")

        # ==========================================================
        # Transcribir el audio a texto
        # ==========================================================
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
        # Procesar el audio con herramientas
        # ==========================================
        inicio = time.time()
        resultado = procesar_audio_con_tools(audio_bytes, user_id)
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