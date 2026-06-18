"""
Expense Service - Gestión de gastos latentes y confirmados.
Maneja el ciclo de vida completo de un gasto desde creación hasta confirmación.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from google import genai

from src.config import GEMINI_API_KEY
from src.logger import logger
from src.services.conversation_state_service import (
    establecer_estado,
    limpiar_estado,
    ESTADO_REGISTRANDO_GASTO,
    ESTADO_IDLE
)

client = genai.Client(api_key=GEMINI_API_KEY)

# =====================================================
# ALMACENAMIENTO EN MEMORIA
# =====================================================

gastos_latentes: Dict[int, Dict] = {}
gastos_confirmados: List[Dict] = []

CATEGORIAS_DISPONIBLES = [
    "Viveres", "Transporte", "Servicios",
    "Entretenimiento", "Tecnologia", "Salud",
    "Educacion", "Otros"
]


# =====================================================
# FUNCIONES AUXILIARES
# =====================================================

def _clasificar_gasto(descripcion: str) -> str:
    """Sugiere categoría basada en descripción usando Gemini."""
    ejemplos = [
        ("Compra supermercado Carrefour", "Viveres"),
        ("Compra en verdulería", "Viveres"),
        ("Carnicería", "Viveres"),
        ("Carga de nafta", "Transporte"),
        ("Uber", "Transporte"),
        ("Netflix", "Servicios"),
        ("Spotify", "Servicios"),
        ("Internet", "Servicios"),
        ("Entrada al cine", "Entretenimiento"),
        ("Steam", "Entretenimiento"),
        ("AWS", "Tecnologia"),
        ("Consulta médica", "Salud"),
        ("Curso de inglés", "Educacion"),
    ]

    categorias_str = ", ".join(CATEGORIAS_DISPONIBLES)

    prompt = f"""
Clasifica el siguiente gasto en UNA SOLA categoría.

Descripción: {descripcion}

Ejemplos:
{chr(10).join(f"- {texto} -> {cat}" for texto, cat in ejemplos)}

Categorías disponibles: {categorias_str}

Devuelve SOLO el nombre exacto de la categoría, sin explicación.
"""

    try:
        response = client.models.generate_content(
            model="gemini-2.5-flash-lite",
            contents=prompt
        )
        categoria = response.text.strip()
        return categoria if categoria in CATEGORIAS_DISPONIBLES else "Otros"
    except Exception as e:
        logger.error(f"Error clasificando gasto: {str(e)}")
        return "Otros"


def _validar_campos(gasto: Dict) -> Tuple[bool, List[str]]:
    """
    Valida que todos los campos requeridos tengan valores.

    Returns:
        (es_valido, campos_faltantes)
    """
    campos_requeridos = [
        "monto", "descripcion", "categoria",
        "efectivo_o_tarjeta"
    ]

    campos_faltantes = []

    for campo in campos_requeridos:
        valor = gasto.get(campo)
        if valor is None or valor == "":
            campos_faltantes.append(campo)

    # Si es tarjeta, también necesita cuotas
    if gasto.get("efectivo_o_tarjeta") == "tarjeta":
        if gasto.get("cuotas") is None:
            campos_faltantes.append("cuotas")
        if gasto.get("monto_por_cuota") is None:
            campos_faltantes.append("monto_por_cuota")

    return len(campos_faltantes) == 0, campos_faltantes


def _get_expense_draft_dict(user_id: int) -> Optional[Dict]:
    """Obtiene el gasto latente como diccionario (uso interno)."""
    return gastos_latentes.get(user_id)


def _formatear_estado_gasto(gasto: Dict) -> str:
    """Formatea un gasto para mostrarlo al usuario."""
    texto = "📊 ESTADO ACTUAL:\n"

    if gasto.get("monto") is not None:
        texto += f"├─ 💰 Monto: ${gasto['monto']} {gasto.get('moneda', 'ARS')}\n"

    if gasto.get("descripcion"):
        texto += f"├─ 📝 Descripción: {gasto['descripcion']}\n"

    if gasto.get("fecha"):
        texto += f"├─ 📅 Fecha: {gasto['fecha']}\n"

    if gasto.get("categoria"):
        texto += f"├─ 📁 Categoría: {gasto['categoria']}\n"
    else:
        texto += f"├─ 📁 Categoría: 🔴 SIN DEFINIR\n"

    if gasto.get("efectivo_o_tarjeta"):
        if gasto["efectivo_o_tarjeta"] == "tarjeta":
            cuotas = gasto.get("cuotas", "?")
            monto_cuota = gasto.get("monto_por_cuota", "?")
            texto += f"├─ 💳 Tarjeta en {cuotas} cuotas de ${monto_cuota}\n"
        else:
            texto += f"├─ 💵 Efectivo\n"
    else:
        texto += f"├─ 🔴 Medio de pago: SIN DEFINIR\n"

    return texto


# =====================================================
# OPERACIONES DE GASTO LATENTE
# =====================================================

def create_expense_draft(user_id: int) -> str:
    """
    Crea un gasto latente/borrador nuevo.

    Returns:
        String confirmando creación
    """
    hoy = datetime.now().strftime("%d/%m/%Y")

    gasto = {
        "user_id": user_id,
        "monto": None,
        "descripcion": None,
        "moneda": "ARS",
        "categoria": None,
        "fecha": hoy,
        "efectivo_o_tarjeta": None,
        "cuotas": None,
        "monto_por_cuota": None,
        "estado": "draft",
        "created_at": datetime.now().isoformat()
    }

    gastos_latentes[user_id] = gasto
    establecer_estado(user_id, ESTADO_REGISTRANDO_GASTO)

    logger.info(f"💼 Gasto latente creado para user_id={user_id}")
    return "✅ Gasto creado. Proporciona detalles (monto, descripción, etc.)"


def update_expense_draft(user_id: int, field: str, value: str) -> str:
    """
    Actualiza un campo del gasto latente.

    Args:
        user_id: ID del usuario
        field: Campo a actualizar
        value: Valor nuevo (como string, se parsea según el campo)

    Returns:
        String con estado actualizado
    """
    if user_id not in gastos_latentes:
        logger.warning(f"⚠️ No hay gasto latente para user_id={user_id}")
        return "❌ No hay gasto en proceso."

    gasto = gastos_latentes[user_id]

    # Conversiones de tipo según el campo
    try:
        if field == "monto" and value:
            gasto[field] = float(value)
        elif field == "cuotas" and value:
            gasto[field] = int(value)
        elif field == "monto_por_cuota" and value:
            gasto[field] = float(value)
        else:
            gasto[field] = value
    except (ValueError, TypeError) as e:
        logger.error(f"Error convirtiendo {field}={value}: {str(e)}")
        return f"❌ Error: No pude procesar {field}={value}"

    # Lógica automática: recalcular monto_por_cuota si cambió monto o cuotas
    if field in ["monto", "cuotas"]:
        if gasto.get("monto") and gasto.get("cuotas"):
            gasto["monto_por_cuota"] = round(gasto["monto"] / gasto["cuotas"], 2)
            logger.info(f"Recalculado monto_por_cuota: {gasto['monto_por_cuota']}")

    # Auto-clasificar categoría si tiene descripción y aún no tiene categoría
    if field == "descripcion" and value and not gasto.get("categoria"):
        gasto["categoria"] = _clasificar_gasto(value)
        logger.info(f"Categoría sugerida: {gasto['categoria']}")

    logger.info(f"✏️ Gasto latente actualizado: {field}={value}")
    return f"✅ {field.capitalize()} actualizado a: {value}"


def get_expense_draft(user_id: int) -> str:
    """
    Obtiene el estado del gasto latente del usuario.

    Returns:
        String formateado con el estado del gasto
    """
    gasto = gastos_latentes.get(user_id)

    if not gasto:
        logger.warning(f"⚠️ No hay gasto latente para user_id={user_id}")
        return "No hay gasto en proceso."

    return _formatear_estado_gasto(gasto)


def get_missing_fields(user_id: int) -> str:
    """
    Obtiene los campos faltantes.

    Returns:
        String con los campos que faltan o "COMPLETO"
    """
    gasto = gastos_latentes.get(user_id)

    if not gasto:
        return "No hay gasto en proceso."

    _, campos_faltantes = _validar_campos(gasto)

    if not campos_faltantes:
        return "COMPLETO"

    return ", ".join(campos_faltantes)


def confirm_expense_draft(user_id: int) -> str:
    """
    Confirma y guarda el gasto latente.

    Returns:
        String confirmando guardado o indicando qué falta
    """
    gasto = gastos_latentes.get(user_id)

    if not gasto:
        logger.error(f"❌ No hay gasto latente para user_id={user_id}")
        return "❌ No hay gasto en proceso."

    # Validar que todos los campos están completos
    es_valido, campos_faltantes = _validar_campos(gasto)

    if not es_valido:
        logger.warning(f"⚠️ Gasto incompleto. Falta: {campos_faltantes}")
        return f"⏳ Falta información: {', '.join(campos_faltantes)}"

    # Cambiar estado a confirmado
    gasto["estado"] = "confirmed"

    # Guardar en lista de confirmados
    gastos_confirmados.append(gasto.copy())

    # Remover de latentes
    del gastos_latentes[user_id]

    # Limpiar estado de conversación
    limpiar_estado(user_id)

    logger.info(f"✅ Gasto confirmado para user_id={user_id}")
    return (
        f"✅✅✅ GASTO REGISTRADO:\n"
        f"💰 ${gasto.get('monto')} {gasto.get('moneda')}\n"
        f"📝 {gasto.get('descripcion')}\n"
        f"📁 {gasto.get('categoria')}\n"
        f"💳 {gasto.get('efectivo_o_tarjeta')}"
    )


def cancel_expense_draft(user_id: int) -> bool:
    """
    Cancela el gasto latente.

    Returns:
        True si fue cancelado exitosamente
    """
    if user_id not in gastos_latentes:
        logger.warning(f"⚠️ No hay gasto latente para user_id={user_id}")
        return False

    del gastos_latentes[user_id]
    limpiar_estado(user_id)

    logger.info(f"❌ Gasto latente cancelado para user_id={user_id}")
    return True


# =====================================================
# OPERACIONES COMPATIBLES (LEGADO)
# =====================================================

def crear_gasto_pendiente(user_id: int, descripcion: str, monto: float) -> str:
    """
    Crea un gasto pendiente (compatible con código anterior).
    Usa el nuevo sistema de gasto latente.
    """
    create_expense_draft(user_id)
    update_expense_draft(user_id, "descripcion", descripcion)
    update_expense_draft(user_id, "monto", str(monto))

    gasto = _get_expense_draft_dict(user_id)
    return gasto.get("categoria", "Otros") if gasto else "Otros"


def obtener_gasto_pendiente(user_id: int) -> Optional[Dict]:
    """Obtiene el gasto pendiente (compatible con código anterior)."""
    return _get_expense_draft_dict(user_id)


def confirmar_gasto(user_id: int) -> str:
    """Confirma un gasto (compatible con código anterior)."""
    gasto = confirm_expense_draft(user_id)

    if not gasto:
        return "No hay gastos pendientes."

    return (
        f"✅ Gasto registrado.\n\n"
        f"Descripción: {gasto.get('descripcion')}\n"
        f"Monto: ${gasto.get('monto'):.2f} {gasto.get('moneda')}\n"
        f"Categoría: {gasto.get('categoria')}"
    )


def cancelar_gasto(user_id: int) -> str:
    """Cancela un gasto (compatible con código anterior)."""
    resultado = cancel_expense_draft(user_id)
    return "❌ Registro cancelado." if resultado else "No hay gastos pendientes."


def actualizar_categoria(user_id: int, categoria: str) -> str:
    """Actualiza la categoría (compatible con código anterior)."""
    gasto = get_expense_draft(user_id)

    if not gasto:
        return "No hay gastos pendientes."

    update_expense_draft(user_id, "categoria", categoria)
    return f"✅ Categoría actualizada a {categoria}."