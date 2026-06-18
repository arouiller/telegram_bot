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

from src.services.geography_services import obtener_capital, obtener_pais
from src.services.weather_service import get_weather, get_latitude_and_longitude
from src.services.expense_service import (
    create_expense_draft,
    update_expense_draft,
    get_expense_draft,
    confirm_expense_draft,
    cancel_expense_draft,
    get_missing_fields
)

# Palabras clave para detección local de intención
_PALABRAS_CLAVE_GASTO = [
    "registrar", "gasto", "pagar", "gasté", "pagué",
    "salida", "cuenta", "factura", "costo", "egreso"
]

_PALABRAS_CLAVE_CLIMA = [
    "clima", "temperatura", "lluvia", "tiempo",
    "frío", "calor", "soleado", "nublado", "cielo",
    "nubes", "viento", "humedad", "llueve", "lluvia"
]

_PALABRAS_CLAVE_GEOGRAFIA = [
    "capital", "país", "pais", "ciudad", "ubicación",
    "donde", "dónde", "capital de", "geografía", "geografia"
]

_AVOID_DETECTION = True

def _detect_intention_local(texto: str) -> str:
    """
    Detecta la intención del usuario basado en palabras clave (rápido, local).

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
                tools=[obtener_capital, obtener_pais]
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
                system_instruction="""Eres un asistente especializado en información climática.

Tienes dos herramientas disponibles:
1. get_latitude_and_longitude(localidad, provincia): Convierte una ciudad en coordenadas
2. get_weather(latitud, longitud): Obtiene el clima para esas coordenadas

Cuando el usuario pregunte por clima:
1. Extrae la localidad y provincia del texto
2. Si menciona una ubicación específica, usa get_latitude_and_longitude() primero
3. Luego usa get_weather() con las coordenadas obtenidas
4. Si no menciona ubicación, usa las coordenadas por defecto de Rosario

Proporciona la información de forma clara y amigable.
Siempre responde en español.""",
                model="gemini-2.5-flash",
                temperature=0.2,
                tools=[get_weather, get_latitude_and_longitude]
            ),
            "last_error": None
        }

        # Agente de Detección de Intención
        self.agents["intent_detection"] = {
            "config": AgentConfig(
                name="intent_detector",
                description="Especialista en detectar la intención del usuario",
                system_instruction="Eres un especialista en detectar la intención de un texto. "
                                   "Clasifica ÚNICAMENTE en una de estas categorías: GASTO, CLIMA, GEOGRAFIA u OTRO. "
                                   "Responde solo con la categoría, sin explicación. "
                                   "Ejemplos: 'Gasto 500' → GASTO | '¿Clima?' → CLIMA | '¿Capital de Francia?' → GEOGRAFIA | 'Hola' → OTRO",
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
                system_instruction="""Eres un asistente inteligente de registro de gastos conversacional.

Tu objetivo: Ayudar al usuario a registrar gastos de forma natural, permitiendo cambios y dando visibilidad total del estado.

FUNCIONES DISPONIBLES:
- create_expense_draft(user_id): Crea nuevo gasto
- update_expense_draft(user_id, field, value): Actualiza campo (value siempre como string)
- get_expense_draft(user_id): Lee estado actual del gasto
- get_missing_fields(user_id): Obtiene campos faltantes
- confirm_expense_draft(user_id): Guarda cuando esté completo
- cancel_expense_draft(user_id): Cancela el gasto

FLUJO:
1. El usuario proporciona información del gasto
2. Si no existe gasto → create_expense_draft(user_id)
3. Extrae y actualiza campos con update_expense_draft()
4. Muestra estado con get_expense_draft()
5. Si usuario dice "Registrar" → confirm_expense_draft()
6. Si usuario dice "Cancela" → cancel_expense_draft()

INSTRUCCIONES IMPORTANTES:
- Siempre pasa strings a update_expense_draft (incluso números: "500", "3")
- Después de actualizar, usa get_expense_draft() para mostrar estado
- Antes de confirmar, usa get_missing_fields() para verificar completitud
- Si get_missing_fields() retorna "COMPLETO", puedes confirmar
- Detecta intención: CANCELAR, CAMBIAR, REGISTRAR, ACTUALIZAR
- Responde en español con emojis
- Sé conversacional y natural

CAMPOS REQUERIDOS:
- monto (número > 0)
- descripcion (texto)
- moneda (default: ARS)
- categoria (Víveres | Transporte | Servicios | Entretenimiento | Tecnologia | Salud | Educacion | Otros)
- fecha (default: hoy)
- efectivo_o_tarjeta (efectivo | tarjeta)
- Si tarjeta:
  - cuotas (número > 0)
  - monto_por_cuota (calculado automáticamente)

REGLAS:
- Si el usuario da monto_total ≠ cuotas × monto_por_cuota → preguntar cuál es correcto
- Si cambia monto con cuotas → recalcular automáticamente
- Si falta algo crítico → NO permitir guardar, indicar qué falta
- Responder siempre en español, con emojis para claridad
- Ser conversacional y natural

FORMATO DE RESPUESTA:
- Mostrar estado en bloque legible con emojis
- Marcar con ✅ lo completo, 🔴 lo pendiente
- Dar opciones claras

EJEMPLOS:
Usuario: "Gasto 500 en supermercado"
Tu respuesta:
"✅ Gasto registrado:
📊 ESTADO ACTUAL:
├─ 💰 Monto: $500 ARS
├─ 📝 Descripción: supermercado
├─ 📅 Fecha: 17/06/2026
├─ 📁 Categoría: Víveres (sugerida)
└─ 🔴 Medio de pago: SIN DEFINIR

⏳ PENDIENTE:
└─ 💳 ¿Efectivo o tarjeta?

💬 Di: 'Efectivo', 'Tarjeta', cambiar algo, o 'Cancela'"

Usuario: "Cambiar a 600"
Tu respuesta:
"✅ Monto actualizado:
📊 ESTADO ACTUAL:
├─ 💰 Monto: $600 ARS ← ACTUALIZADO
...
⏳ PENDIENTE:
└─ 💳 ¿Efectivo o tarjeta?"

Usuario: "Registrar gasto"
Tu respuesta (si completo):
"✅✅✅ GASTO REGISTRADO EXITOSAMENTE:
💰 $600 ARS
📝 Supermercado
📁 Víveres
💳 Tarjeta en 3 cuotas de $200 c/u
📅 17/06/2026

🎉 ¡Gasto confirmado!"
""",
                model="gemini-2.5-flash",
                temperature=0.2,
                tools=[
                    create_expense_draft,
                    update_expense_draft,
                    get_expense_draft,
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

    def detect_intention_sync(
        self,
        texto: str,
        temperature: Optional[float] = None
    ) -> str:
        """
        Detecta la intención del usuario con estrategia híbrida.

        Primero intenta detectar con palabras clave (rápido, local).
        Si no es claro (resultado = OTRO), consulta el agente (inteligente).

        Args:
            texto: Texto del usuario
            temperature: Temperatura opcional (por defecto 0.1)

        Returns:
            Intención detectada: GASTO, CLIMA, GEOGRAFIA o OTRO
        """
        try:
            # Paso 1: Intentar con palabras clave (rápido)
            intension_local = _detect_intention_local(texto)

            if intension_local != "OTRO":
                logger.info(f"🎯 Intención detectada localmente: {intension_local}")
                return intension_local

            # Paso 2: Si no es claro, consultar agente (inteligente)
            logger.info(f"❓ Intención no clara, consultando agente...")
            try:
                prompt = f"""
Clasifica la intención en GASTO, CLIMA, GEOGRAFIA u OTRO:
"{texto}"

Responde SOLO con la categoría, sin explicación.
"""
                resultado = self.run_agent_sync("intent_detection", prompt, temperature)
                intension_agente = resultado.strip().upper()
                logger.info(f"🎯 Intención detectada por agente: {intension_agente}")
                return intension_agente

            except Exception as e:
                logger.error(f"Error consultando agente, usando fallback: {str(e)}")
                return "OTRO"

        except Exception as e:
            logger.error(f"Error en detect_intention_sync: {str(e)}")
            raise

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
