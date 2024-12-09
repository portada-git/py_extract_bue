from openai import OpenAI
import os
import json
from config import MODELO, JSON_SCHEMA, MODEL_CONFIG
from common import create_messages

class InfoExtractor:
    def __init__(self):
        """
        Inicializa el extractor con la API key de OpenAI
        """
        self.client = OpenAI(api_key=os.environ.get("OPENAI_API_KEY"))
    
    def extraer_informacion(self, texto):
        """
        Extrae información estructurada de un arribo
        Args:
            texto (str): Texto de la nota a procesar
        Returns:
            dict: Información estructurada en formato JSON o None si hay error
        """
        try:
            respuesta = self.client.chat.completions.create(
                model=MODELO,
                messages=create_messages(texto),
                response_format=JSON_SCHEMA,
                **MODEL_CONFIG
            )
            
            return json.loads(respuesta.choices[0].message.content)
            
        except Exception as e:
            print(f"Error al procesar la nota: {str(e)}")
            return None
