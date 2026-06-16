"""
Ejemplos de cómo usar el AgentOrchestrator en diferentes contextos.
Estos son patrones recomendados para integrar agentes en los handlers.
"""

from src.services.agent_orchestrator import orchestrator
from src.logger import logger


# ===== EJEMPLO 1: Usar agente de geografía =====
def get_capital_via_agent(country: str) -> str:
    """
    Obtiene la capital de un país usando el agente de geografía.

    Args:
        country: Nombre del país

    Returns:
        Respuesta del agente con la capital
    """
    try:
        prompt = f"¿Cuál es la capital de {country}?"
        result = orchestrator.run_agent_sync("geography", prompt)
        return result
    except Exception as e:
        logger.error(f"Error en get_capital_via_agent: {str(e)}")
        return "No pude obtener la información. Intenta de nuevo."


# ===== EJEMPLO 2: Consulta de geografía más compleja =====
def geography_query(query: str) -> str:
    """
    Consulta general de geografía usando el agente.

    Args:
        query: Pregunta sobre geografía

    Returns:
        Respuesta del agente
    """
    try:
        # El agente tiene acceso a herramientas de obtener_capital y obtener_pais
        result = orchestrator.run_agent_sync("geography", query, temperature=0.3)
        return result
    except Exception as e:
        logger.error(f"Error en geography_query: {str(e)}")
        return "Error procesando tu pregunta sobre geografía."


# ===== EJEMPLO 3: Transcripción de audio =====
def transcribe_audio_via_agent(audio_path: str) -> str:
    """
    Transcribe audio usando el agente de voz.

    Args:
        audio_path: Ruta al archivo de audio

    Returns:
        Transcripción del audio
    """
    try:
        # Para audio, puedes crear un prompt que incluya contexto
        prompt = f"Transcribe el audio en: {audio_path}"
        result = orchestrator.run_agent_sync("voice", prompt, temperature=0.2)
        return result
    except Exception as e:
        logger.error(f"Error en transcribe_audio_via_agent: {str(e)}")
        return "Error transcribiendo el audio."


# ===== EJEMPLO 4: Información climática =====
def get_weather_via_agent() -> str:
    """
    Obtiene información climática usando el agente de clima.

    Returns:
        Información del clima formateada
    """
    try:
        prompt = "¿Cuál es el clima actual? Incluye temperatura, humedad y descripción."
        result = orchestrator.run_agent_sync("weather", prompt, temperature=0.2)
        return result
    except Exception as e:
        logger.error(f"Error en get_weather_via_agent: {str(e)}")
        return "No pude obtener la información del clima."


# ===== EJEMPLO 5: Consulta general a agente específico =====
def query_agent(agent_name: str, prompt: str, temperature: float = None) -> str:
    """
    Interfaz genérica para consultar cualquier agente.

    Args:
        agent_name: Nombre del agente ('geography', 'voice', 'weather')
        prompt: Pregunta o prompt para el agente
        temperature: Temperatura opcional (0-1)

    Returns:
        Respuesta del agente o mensaje de error
    """
    try:
        # Valida que el agente exista
        if agent_name not in orchestrator.list_agents():
            available = ", ".join(orchestrator.list_agents())
            return f"Agente '{agent_name}' no encontrado. Disponibles: {available}"

        result = orchestrator.run_agent_sync(agent_name, prompt, temperature)
        return result
    except Exception as e:
        logger.error(f"Error en query_agent({agent_name}): {str(e)}")
        return f"Error consultando agente '{agent_name}'."


# ===== EJEMPLO 6: Integración en un handler (patrón recomendado) =====
"""
Cómo usarlo en message_handlers.py:

from src.services.agent_usage_examples import geography_query

@bot.message_handler(func=lambda message: message.text and message.text.lower() == 'geografía')
def handle_geography(message):
    try:
        bot.send_message(message.chat.id, "Procesando consulta de geografía...")
        result = geography_query(message.text)
        bot.send_message(message.chat.id, result)
    except Exception as e:
        logger.error(f"Error en handler geografía: {str(e)}")
        bot.send_message(message.chat.id, "Error procesando tu consulta.")
"""


# ===== EJEMPLO 7: Obtener información de un agente =====
def get_agent_info(agent_name: str) -> dict:
    """
    Obtiene información sobre un agente específico.

    Args:
        agent_name: Nombre del agente

    Returns:
        Diccionario con información del agente
    """
    return orchestrator.get_agent_info(agent_name)


# ===== EJEMPLO 8: Listar agentes disponibles =====
def list_available_agents() -> list:
    """
    Lista todos los agentes disponibles.

    Returns:
        Lista de nombres de agentes
    """
    return orchestrator.list_agents()


# ===== EJEMPLO 9: Obtener estado general =====
def get_orchestrator_status() -> dict:
    """
    Obtiene el estado general del orquestador.

    Returns:
        Diccionario con estado de todos los agentes
    """
    return orchestrator.get_status()
