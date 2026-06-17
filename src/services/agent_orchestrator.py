"""
Agent Orchestrator - Centraliza la ejecución de agentes de Google ADK.
Proporciona una interfaz unificada para ejecutar diferentes agentes especializados.
"""

import logging
from typing import Dict, Any, Optional, List
from dataclasses import dataclass

from google.adk import Agent
from google import genai
from google.genai import types

from src.config import GEMINI_API_KEY
from src.logger import logger


@dataclass
class AgentConfig:
    """Configuración de un agente."""
    name: str
    description: str
    system_instruction: str
    model: str = "gemini-2.5-flash"
    temperature: float = 0.3
    tools: Optional[List] = None


class AgentOrchestrator:
    """
    Orquestador central de agentes ADK.
    Gestiona la creación, configuración y ejecución de agentes especializados.
    """

    def __init__(self):
        """Inicializa el orquestador y los agentes."""
        self.client = genai.Client(api_key=GEMINI_API_KEY)
        self.agents: Dict[str, Dict[str, Any]] = {}
        self._initialize_agents()
        logger.info("AgentOrchestrator inicializado")

    def _initialize_agents(self) -> None:
        """Inicializa todos los agentes disponibles."""

        # Agente de Geografía
        self.agents["geography"] = {
            "config": AgentConfig(
                name="geography_assistant",
                description="Especialista en geografía, capitales y ubicaciones",
                system_instruction="Eres un asistente experto en geografía llamado asistente_geografico. "
                                   "Usa tus herramientas para responder preguntas sobre capitales y países. "
                                   "Responde en español.",
                model="gemini-2.5-flash",
                temperature=0.3,
                tools=[self._obtener_capital, self._obtener_pais]
            ),
            "last_error": None
        }

        # Agente de Voz
        self.agents["transcripcion"] = {
            "config": AgentConfig(
                name="voice_assistant",
                description="Especialista en transcripción y procesamiento de audio",
                system_instruction="Eres un asistente especializado en transcribir y analizar audio. "
                                   "Devuelve transcripciones claras y precisas en español.",
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
                description="Especialista en información meteorológica",
                system_instruction="Eres un asistente especializado en información climática. "
                                   "Proporciona datos de temperatura, humedad y condiciones del tiempo. "
                                   "Responde en español.",
                model="gemini-2.5-flash",
                temperature=0.2,
                tools=[self._obtener_clima]
            ),
            "last_error": None
        }

    def _obtener_capital(self, pais: str) -> str:
        """Tool: Obtiene la capital de un país."""
        capitales = {
            "Francia": "París",
            "Japón": "Tokio",
            "Argentina": "Buenos Aires"
        }
        return capitales.get(pais, "Capital desconocida")

    def _obtener_pais(self, capital: str) -> str:
        """Tool: Obtiene el país de una capital."""
        capitales = {
            "Francia": "París",
            "Japón": "Tokio",
            "Argentina": "Buenos Aires"
        }
        for pais, cap in capitales.items():
            if cap == capital:
                return pais
        return "País desconocido"

    def _obtener_clima(self) -> str:
        """Tool: Obtiene información climática actual."""
        # Placeholder - será reemplazado por integración real de weather_service
        return "Temperatura: 25°C, Humedad: 60%, Soleado"

    async def run_agent(
        self,
        agent_name: str,
        prompt: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Ejecuta un agente con un prompt específico.

        Args:
            agent_name: Nombre del agente ('geography', 'voice', 'weather')
            prompt: Mensaje de entrada para el agente
            temperature: Temperatura opcional (sobrescribe la configuración)

        Returns:
            Respuesta del agente como string

        Raises:
            ValueError: Si el agente no existe
            Exception: Si hay error en la ejecución del agente
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
        Versión síncrona de run_agent (compatible con código existente).

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
        Transcribe audio usando el agente de transcripción.

        Args:
            audio_bytes: Bytes del archivo de audio
            temperature: Temperatura opcional (por defecto 0.2)

        Returns:
            Texto transcrito

        Raises:
            Exception: Si hay error en la transcripción
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

            logger.info("Transcripción completada exitosamente")
            agent_data["last_error"] = None

            return response.text.strip()

        except Exception as e:
            error_msg = f"Error transcribiendo audio: {str(e)}"
            logger.error(error_msg)
            agent_data["last_error"] = str(e)
            raise Exception(error_msg)

    def get_agent_info(self, agent_name: str) -> Dict[str, Any]:
        """Obtiene información sobre un agente."""
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
