import os
import json
from babel.dates import format_date
from utils import procesar_archivo

nombre_archivo = './txt/1880_03_04_BUE_LP_U_00_000_MasterLimpio.txt'
directorio_salida = './json'

if __name__ == "__main__":
    ruta_absoluta = os.path.abspath(nombre_archivo)
    nombre_base = os.path.basename(ruta_absoluta)

    try:
        with open(ruta_absoluta, 'r', encoding='utf-8') as file:
            contenido = file.read()
            resultados = procesar_archivo(nombre_base, contenido)

        os.makedirs(directorio_salida, exist_ok=True)
        nombre_salida = f"{os.path.splitext(nombre_base)[0]}_procesado.json"
        ruta_salida = os.path.join(directorio_salida, nombre_salida)
        
        with open(ruta_salida, 'w', encoding='utf-8') as f:
            json.dump(resultados, f, ensure_ascii=False, indent=2)
        
    except FileNotFoundError:
        print(f"Error: No se pudo encontrar el archivo '{nombre_archivo}'")
    except Exception as e:
        print(f"Error al procesar el archivo: {str(e)}")

print(json.dumps(resultados[:5], ensure_ascii=False, indent=2))
