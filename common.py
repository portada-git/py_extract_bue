import re
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from babel.dates import format_date
from regex import METADATA_PATTERN, DIA_PATTERN, ENTRADA_PATTERN
from config import FIELD_DEFINITIONS, MESSAGES_CONFIG, JSON_TEMPLATE, EXAMPLES

def create_messages(texto_entrada):
    """
    Crea la lista de mensajes para la API de OpenAI
    """
    # Formateamos las definiciones de campos como texto
    field_definitions_text = '. '.join([
        f"'{key}': '{value}'" 
        for key, value in FIELD_DEFINITIONS.items()
    ])

    # Creamos el mensaje del usuario con el template
    user_message = MESSAGES_CONFIG["template"]["content"].format(
        json_template=JSON_TEMPLATE,
        field_definitions=field_definitions_text,
        input_example=EXAMPLES,
        input_text=texto_entrada
    )

    # Retornamos la lista completa de mensajes
    return [
        MESSAGES_CONFIG["system"],
        {"role": "user", "content": user_message}
    ]

def calcular_fecha_entrada(fecha_nota: str, dia: str) -> Optional[datetime]:
    """
    Calcula la fecha de entrada basada en la fecha de la nota y el día.
    """
    try:
        fecha_nota = datetime.strptime(fecha_nota, '%Y_%m_%d')
        dia = int(dia)
        
        if dia <= fecha_nota.day:
            return fecha_nota - timedelta(days=fecha_nota.day - dia)
        else:
            fecha_anterior = fecha_nota.replace(day=1) - timedelta(days=1)
            return fecha_anterior - timedelta(days=fecha_anterior.day - dia)
    except ValueError:
        return None

def formato_fecha_espanol(fecha: Optional[datetime]) -> str:
    """
    Formatea la fecha en español.
    """
    if fecha:
        return format_date(fecha, format='d \'de\' MMMM \'de\' yyyy', locale='es')
    return "Fecha desconocida"
