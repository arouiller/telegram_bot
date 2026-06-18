"""
Agent Orchestrator - Centraliza la ejecuciÃ³n de agentes de Google ADK.
Proporciona una interfaz unificada para ejecutar diferentes agentes especializados.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass
from pathlib import Path

from google.adk import Agent
from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY
from src.logger import logger

from src.services.geography_services import obtener_capital, obtener_pais
from src.services.weather_service import get_weather, get_latitude_and_longitude
from src.services.expense_service import (
    create_or_get_expense_draft,
    update_expense_draft,
    confirm_expense_draft,
    cancel_expense_draft,
    get_missing_fields
)

# Palabras clave para detecciÃ³n local de intenciÃ³n
_PALABRAS_CLAVE_GASTO = [
    "registrar", "gasto", "pagar", "gastÃ©", "paguÃ©",
    "salida", "cuenta", "factura", "costo", "egreso"
]

_PALABRAS_CLAVE_CLIMA = [
    "clima", "temperatura", "lluvia", "tiempo",
    "frÃ­o", "calor", "soleado", "nublado", "cielo",
    "nubes", "viento", "humedad", "llueve", "lluvia"
]

_PALABRAS_CLAVE_GEOGRAFIA = [
    "capital", "paÃ­s", "pais", "ciudad", "ubicaciÃ³n",
    "donde", "dÃ³nde", "capital de", "geografÃ­a", "geografia"
]

_AVOID_DETECTION = True

# =====================================================
# CARGA DE PROMPTS
# =====================================================

PROMPTS_DIR = Path(__file__).parent.parent / "prompts"

def _load_prompt(agent_name: str) -> str:
    """
    Carga el prompt de un archivo de texto.

    Args:
        agent_name: Nombre del agente (geography, transcripcion, weather, expense)

    Returns:
        Contenido del archivo prompt
    """
    prompt_file = PROMPTS_DIR / f"{agent_name}.txt"

    try:
        with open(prompt_file, "r", encoding="utf-8") as f:
            return f.read().strip()
    except FileNotFoundError:
        logger.error(f"âŒ Archivo de prompt no encontrado: {prompt_file}")
        return f"Error cargando prompt para {agent_name}"


def _detect_intention_local(texto: str) -> str:
    """
    Detecta la intenciÃ³n del usuario basado en palabras clave (rÃ¡pido, local).

    Args:
        texto: Texto del usuario

    Returns:
        GASTO, CLIMA, GEOGRAFIA o OTRO
    """

    if _AVOID_DETECTION:
        return "OTRO"

    texto_lower = texto.lower()

    if any(palabra in texto_lower for palabra in _PALABRAS_CLAVE_GASTO):
        return "GASTO"

    if any(palabra in texto_lower for palabra in _PALABRAS_CLAVE_CLIMA):
        return "CLIMA"

    if any(palabra in texto_lower for palabra in _PALABRAS_CLAVE_GEOGRAFIA):
        return "GEOGRAFIA"

    return "OTRO"


@dataclass
class AgentConfig:
    """ConfiguraciÃ³n de un agente."""
    name: str
    description: str
    system_instruction: str
    model: str = "gemini-2.5-flash"
    temperature: float = 0.3
    tools: Optional[List] = None


class AgentOrchestrator:
    """
    Orquestador central de agentes ADK.
    Gestiona la creaciÃ³n, configuraciÃ³n y ejecuciÃ³n de agentes especializados.
    """

    def __init__(self):
        """Inicializa el orquestador y los agentes."""
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self._initialize_agents()
        logger.info("AgentOrchestrator inicializado")

    def _initialize_agents(self) -> None:
        """Inicializa todos los agentes disponibles."""

        # Agente de GeografÃ­a
        self.agents["geography"] = {
            "config": AgentConfig(
                name="geography_assistant",
                description="Especialista en geografÃ­a, capitales y ubicaciones",
                system_instruction=_load_prompt("geography"),
                model="gemini-2.5-flash",
                temperature=0.3,
                tools=[obtener_capital, obtener_pais]
            ),
            "last_error": None
        }

        # Agente de Voz
        self.agents["transcripcion"] = {
            "config": AgentConfig(
                name="voice_assistant",
                description="Especialista en transcripciÃ³n y procesamiento de audio",
                system_instruction=_load_prompt("transcripcion"),
                model="gemini-2.5-flash-lite",
                temperature=0.2,
                tools=None
            ),
            "last_error": None
        }

        # Agente de Clima
        self.agents["weather"] = {
            "config": AgentConfig(
                name="weather_assistant",
                description="Especialista en informaciÃ³n meteorolÃ³gica",
                system_instruction=_load_prompt("weather"),
                model="gemini-2.5-flash",
                temperature=0.2,
                tools=[get_weather, get_latitude_and_longitude]
            ),
            "last_error": None
        }

        # Agente de DetecciÃ³n de IntenciÃ³n
        self.agents["intent_detection"] = {
            "config": AgentConfig(
                name="intent_detector",
                description="Especialista en detectar la intenciÃ³n del usuario",
                system_instruction="Eres un especialista en detectar la intenciÃ³n de un texto. "
                                   "Clasifica ÃšNICAMENTE en una de estas categorÃ­as: GASTO, CLIMA, GEOGRAFIA u OTRO. "
                                   "Responde solo con la categorÃ­a, sin explicaciÃ³n. "
                                   "Ejemplos: 'Gasto 500' â†’ GASTO | 'Â¿Clima?' â†’ CLIMA | 'Â¿Capital de Francia?' â†’ GEOGRAFIA | 'Hola' â†’ OTRO",
                model="gemini-2.5-flash",
                temperature=0.1,
                tools=None
            ),
            "last_error": None
        }

        # Agente de Gastos
        self.agents["expense"] = {
            "config": AgentConfig(
                name="expense_assistant",
                description="Especialista en registro conversacional de gastos",
                system_instruction=_load_prompt("expense"),
                model="gemini-2.5-flash",
                temperature=0.2,
                tools=[
                    create_or_get_expense_draft,
                    update_expense_draft,
                    confirm_expense_draft,
                    cancel_expense_draft,
                    get_missing_fields
                ]
            ),
            "last_error": None
        }

    async def run_agent(
        self,
        agent_name: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Ejecuta un agente con un prompt especÃ­fico.

        Args:
            agent_name: Nombre del agente ('geography', 'voice', 'weather')
            prompt: Mensaje de entrada para el agente
            temperature: Temperatura opcional (sobrescribe la configuraciÃ³n)

        Returns:
            Respuesta del agente como string

        Raises:
            ValueError: Si el agente no existe
            Exception: Si hay error en la ejecuciÃ³n del agente
        """
        if agent_name not in self.agents:
            raise ValueError(f"Agente '{agent_name}' no encontrado. "
                           f"Disponibles: {list(self.agents.keys())}")

        agent_data = self.agents[agent_name]
        config = agent_data["config"]

        try:
            logger.info(f"Ejecutando agente '{agent_name}' con prompt: {prompt[:50]}...")

            # Usa temperatura personalizada si se proporciona
            temp = temperature if temperature is not None else config.temperature

            response = self.client.models.generate_content(
                model=config.model,
                contents=prompt,
                config={
                    "system_instruction": config.system_instruction,
                    "tools": config.tools,
                    "temperature": temp,
                }
            )

            logger.info(f"Agente '{agent_name}' ejecutado exitosamente")
            agent_data["last_error"] = None

            return response.text

        except Exception as e:
            error_msg = f"Error ejecutando agente '{agent_name}': {str(e)}"
            logger.error(error_msg)
            agent_data["last_error"] = str(e)
            raise Exception(error_msg)

    def run_agent_sync(
        self,
        agent_name: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        VersiÃ³n sÃ­ncrona de run_agent (compatible con cÃ³digo existente).

        Args:
            agent_name: Nombre del agente
            prompt: Mensaje de entrada
            temperature: Temperatura opcional

        Returns:
            Respuesta del agente
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        return loop.run_until_complete(
            self.run_agent(agent_name, prompt, temperature)
        )

    def transcribe_audio_sync(
        self,
        audio_bytes: bytes,
        temperature: Optional[float] = None
    ) -> str:
        """
        Transcribe audio usando el agente de transcripciÃ³n.

        Args:
            audio_bytes: Bytes del archivo de audio
            temperature: Temperatura opcional (por defecto 0.2)

        Returns:
            Texto transcrito

        Raises:
            Exception: Si hay error en la transcripciÃ³n
        """
        agent_data = self.agents["transcripcion"]
        config = agent_data["config"]

        try:
            logger.info("Transcribiendo audio con agente 'transcripcion'...")

            temp = temperature if temperature is not None else config.temperature

            response = self.client.models.generate_content(
                model=config.model,
                contents=[
                    config.system_instruction,
                    types.Part.from_bytes(
                        data=audio_bytes,
                        mime_type="audio/ogg"
                    )
                ],
                config={
                    "temperature": temp,
                }
            )

            logger.info("TranscripciÃ³n completada exitosamente")
            agent_data["last_error"] = None

            return response.text.strip()

        except Exception as e:
            error_msg = f"Error transcribiendo audio: {str(e)}"
            logger.error(error_msg)
            agent_data["last_error"] = str(e)
            raise Exception(error_msg)

    def detect_intention_sync(
        self,
        texto: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Detecta la intenciÃ³n del usuario con estrategia hÃ­brida.

        Primero intenta detectar con palabras clave (rÃ¡pido, local).
        Si no es claro (resultado = OTRO), consulta el agente (inteligente).

        Args:
            texto: Texto del usuario
            temperature: Temperatura opcional (por defecto 0.1)

        Returns:
            IntenciÃ³n detectada: GASTO, CLIMA, GEOGRAFIA o OTRO
        """
        try:
            # Paso 1: Intentar con palabras clave (rÃ¡pido)
            intension_local = _detect_intention_local(texto)

            if intension_local != "OTRO":
                logger.info(f"ðŸŽ¯ IntenciÃ³n detectada localmente: {intension_local}")
                return intension_local

            # Paso 2: Si no es claro, consultar agente (inteligente)
            logger.info(f"â“ IntenciÃ³n no clara, consultando agente...")
            try:
                prompt = f"""
Clasifica la intenciÃ³n en GASTO, CLIMA, GEOGRAFIA u OTRO:
"{texto}"

Responde SOLO con la categorÃ­a, sin explicaciÃ³n.
"""
                resultado = self.run_agent_sync("intent_detection", prompt, temperature)
                intension_agente = resultado.strip().upper()
                logger.info(f"ðŸŽ¯ IntenciÃ³n detectada por agente: {intension_agente}")
                return intension_agente

            except Exception as e:
                logger.error(f"Error consultando agente, usando fallback: {str(e)}")
                return "OTRO"

        except Exception as e:
            logger.error(f"Error en detect_intention_sync: {str(e)}")
            raise

    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Obtiene informaciÃ³n sobre un agente."""
        if agent_name not in self.agents:
            return {"error": f"Agente '{agent_name}' no encontrado"}

        agent_data = self.agents[agent_name]
        config = agent_data["config"]

        return {
            "name": config.name,
            "description": config.description,
            "model": config.model,
            "temperature": config.temperature,
            "has_tools": config.tools is not None and len(config.tools) > 0,
            "last_error": agent_data["last_error"]
        }

    def list_agents(self) -> List[str]:
        """Lista todos los agentes disponibles."""
        return list(self.agents.keys())

    def get_status(self) -> Dict[str, Any]:
        """Obtiene el estado general del orquestador."""
        return {
            "agents": [
                {
                    "name": name,
                    "info": self.get_agent_info(name)
                }
                for name in self.list_agents()
            ],
            "client_initialized": self.client is not None
        }


# Instancia global del orquestador
orchestrator = AgentOrchestrator()
