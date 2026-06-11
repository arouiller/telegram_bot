# src/services/expense_service.py
import os
from google import genai
from telebot import logger

from src.config import GEMINI_API_KEY
from src.logger import logger

client = genai.Client(
    api_key=GEMINI_API_KEY
)

# =====================================================
# ESTADO TEMPORAL
# =====================================================

gastos_pendientes = {}

# =====================================================
# CLASIFICADOR
# =====================================================

def clasificar_gasto(descripcion: str) -> str:

    ejemplos = [
        ("Compra supermercado Carrefour", "Viveres"),
        ("Compra en verdulería", "Viveres"),
        ("Carnicería", "Viveres"),
        ("Agua mineral", "Viveres"),

        ("Carga de nafta", "Transporte"),
        ("Uber", "Transporte"),
        ("Taxi", "Transporte"),

        ("Netflix", "Servicios"),
        ("Spotify", "Servicios"),
        ("Internet", "Servicios"),
        ("Luz", "Servicios"),
        ("Gas", "Servicios"),

        ("Entrada al cine", "Entretenimiento"),
        ("Steam", "Entretenimiento"),
        ("Concierto", "Entretenimiento"),

        ("AWS", "Tecnologia"),
        ("Servidor VPS", "Tecnologia"),

        ("Consulta médica", "Salud"),
        ("Medicamentos", "Salud"),

        ("Curso de inglés", "Educacion"),
        ("Libros", "Educacion")
    ]

    categorias = sorted(
        {
            categoria
            for _, categoria in ejemplos
        }
    )

    prompt = f"""
Clasifica el siguiente gasto.

Descripción:
{descripcion}

Ejemplos:

{chr(10).join(
    f"- {texto} -> {categoria}"
    for texto, categoria in ejemplos
)}

Categorías disponibles:

{", ".join(categorias)}

Devuelve únicamente el nombre exacto
de la categoría.
"""

    response = client.models.generate_content(
        model="gemini-2.5-flash-lite",
        contents=prompt
    )

    categoria = response.text.strip()

    if categoria not in categorias:
        return "Otros"

    return categoria

# =====================================================
# OPERACIONES
# =====================================================

def crear_gasto_pendiente(
    user_id: int,
    descripcion: str,
    monto: float
):
    logger.info(
        f"GUARDANDO PENDIENTE user={user_id}"
    )

    categoria = clasificar_gasto(
        descripcion
    )

    gastos_pendientes[user_id] = {
        "descripcion": descripcion,
        "monto": monto,
        "categoria": categoria
    }

    return categoria


def obtener_gasto_pendiente(
    user_id: int
):

    logger.info(
        f"PID={os.getpid()} "
        f"gastos={gastos_pendientes}"
    )

    return gastos_pendientes.get(
        user_id
    )


def confirmar_gasto(
    user_id: int
) -> str:

    gasto = gastos_pendientes.get(
        user_id
    )

    if not gasto:
        return (
            "No hay gastos pendientes."
        )

    # FUTURO:
    #
    # guardar_en_bd(
    #     gasto["descripcion"],
    #     gasto["monto"],
    #     gasto["categoria"]
    # )

    del gastos_pendientes[user_id]

    return (
        f"Gasto registrado.\n\n"
        f"Descripción: "
        f"{gasto['descripcion']}\n"
        f"Monto: "
        f"${gasto['monto']:.2f}\n"
        f"Categoría: "
        f"{gasto['categoria']}"
    )


def cancelar_gasto(
    user_id: int
) -> str:

    if user_id in gastos_pendientes:

        del gastos_pendientes[user_id]

        return "Registro cancelado."

    return "No hay gastos pendientes."


def actualizar_categoria(
    user_id: int,
    categoria: str
) -> str:

    gasto = gastos_pendientes.get(
        user_id
    )

    if not gasto:
        return (
            "No hay gastos pendientes."
        )

    gasto["categoria"] = categoria

    return (
        f"Categoría actualizada a "
        f"{categoria}."
    )