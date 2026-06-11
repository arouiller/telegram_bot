# src/services/conversation_state_service.py

ESTADO_IDLE = "IDLE"

ESTADO_ESPERANDO_CONFIRMACION_GASTO = (
    "ESPERANDO_CONFIRMACION_GASTO"
)

_estados = {}


def obtener_estado(user_id: int):

    return _estados.get(
        user_id,
        {
            "estado": ESTADO_IDLE,
            "data": {}
        }
    )


def establecer_estado(
    user_id: int,
    estado: str,
    data: dict | None = None
):

    _estados[user_id] = {
        "estado": estado,
        "data": data or {}
    }


def limpiar_estado(user_id: int):

    _estados[user_id] = {
        "estado": ESTADO_IDLE,
        "data": {}
    }