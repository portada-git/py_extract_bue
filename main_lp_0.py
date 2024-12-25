import os
import json
import re
from config_lp_prueba import procesar_archivo

directorio_entrada = './txt/master_lp/'
directorio_salida = './json/json_master/'

def main():
    try:
        os.makedirs(directorio_salida, exist_ok=True)

        for nombre_archivo in os.listdir(directorio_entrada):
            if nombre_archivo.endswith('.txt'):
                ruta_absoluta = os.path.join(directorio_entrada, nombre_archivo)

                with open(ruta_absoluta, 'r', encoding='utf-8') as file:
                    contenido = file.read()
                    resultados = procesar_archivo(nombre_archivo, contenido)

                nombre_salida = f"{os.path.splitext(nombre_archivo)[0]}_procesado.json"
                ruta_salida = os.path.join(directorio_salida, nombre_salida)
                
                with open(ruta_salida, 'w', encoding='utf-8') as f:
                    json.dump(resultados, f, ensure_ascii=False, indent=2)

    except Exception as e:
        print(f"Error al procesar los archivos: {str(e)}")

if __name__ == "__main__":
    main()
