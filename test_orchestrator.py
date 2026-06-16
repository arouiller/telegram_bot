"""
Script de prueba del AgentOrchestrator.
Ejecuta pruebas básicas para verificar que los agentes funcionan correctamente.

Uso:
    python test_orchestrator.py
"""

import sys
from pathlib import Path

# Agrega el directorio raíz al path
sys.path.insert(0, str(Path(__file__).parent))

from src.services.agent_orchestrator import orchestrator
from src.services.agent_usage_examples import (
    list_available_agents,
    get_agent_info,
    geography_query,
    get_orchestrator_status
)
from src.logger import logger


def test_orchestrator():
    """Ejecuta pruebas del orchestrator."""
    print("\n" + "="*60)
    print("PRUEBA: Agent Orchestrator")
    print("="*60 + "\n")

    # Test 1: Listar agentes disponibles
    print("📋 Test 1: Listar agentes disponibles")
    try:
        agents = list_available_agents()
        print(f"   ✓ Agentes encontrados: {agents}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 2: Obtener información de agentes
    print("\n📋 Test 2: Información de agentes")
    try:
        for agent_name in list_available_agents():
            info = get_agent_info(agent_name)
            print(f"\n   Agente: {agent_name}")
            print(f"   - Descripción: {info.get('description', 'N/A')}")
            print(f"   - Modelo: {info.get('model', 'N/A')}")
            print(f"   - Temperatura: {info.get('temperature', 'N/A')}")
            print(f"   - Tiene tools: {info.get('has_tools', False)}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 3: Consulta simple al agente de geografía
    print("\n📋 Test 3: Consulta al agente de geografía")
    try:
        query = "¿Cuál es la capital de Francia?"
        print(f"   Pregunta: {query}")
        response = geography_query(query)
        print(f"   Respuesta: {response[:200]}...")
        print("   ✓ Consulta exitosa")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    # Test 4: Obtener estado del orquestador
    print("\n📋 Test 4: Estado del orquestador")
    try:
        status = get_orchestrator_status()
        print(f"   ✓ Orquestador activo con {len(status['agents'])} agentes")
        print(f"   - Cliente inicializado: {status['client_initialized']}")
    except Exception as e:
        print(f"   ✗ Error: {e}")

    print("\n" + "="*60)
    print("PRUEBAS COMPLETADAS")
    print("="*60 + "\n")


if __name__ == "__main__":
    try:
        test_orchestrator()
    except KeyboardInterrupt:
        print("\n⚠️ Pruebas interrumpidas por el usuario")
    except Exception as e:
        print(f"\n❌ Error inesperado: {e}")
        logger.error(f"Error en test_orchestrator: {e}")
