import re
from common import calcular_fecha_entrada, formato_fecha_espanol
from regex import METADATA_PATTERN, DIA_PATTERN, ENTRADA_PATTERN
from extractor import InfoExtractor

def procesar_archivo(nombre_archivo: str, contenido: str):
    """
    Procesa un archivo y extrae la información relevante.
    """
    match = METADATA_PATTERN.search(contenido)
    metadata = match.group(1) if match else "Fecha no encontrada"
    
    dia_match = DIA_PATTERN.search(metadata)
    dia = dia_match.group(1) if dia_match else ""
    
    fecha_nota = nombre_archivo[:10] if len(nombre_archivo) >= 10 else ""
    
    nueva_fecha_entrada = calcular_fecha_entrada(fecha_nota, dia)
    fecha_arribo_texto = formato_fecha_espanol(nueva_fecha_entrada)
    
    contenido_limpio = re.sub(r'^' + re.escape(metadata), '', contenido, flags=re.MULTILINE).strip()
    
    entradas = ENTRADA_PATTERN.split(contenido_limpio)
    
    datos = []
    
    extractor = InfoExtractor()
    
    for entrada in entradas:
        if entrada.strip():
            entrada_con_fecha = f"Fecha de arribo: {fecha_arribo_texto} | {entrada.strip()}"
            
            try:
                resultado_json = extractor.extraer_informacion(entrada_con_fecha)
            except Exception as e:
                print(f"Error al procesar la entrada con InfoExtractor: {str(e)}")
                resultado_json = {"error": "No se pudo procesar la entrada"}
            
            datos.append({
                'name_txt': nombre_archivo,
                'fecha_nota': fecha_nota,
                'metadata_entrada': metadata.strip(),
                'dia': dia,
                'fecha_entrada': nueva_fecha_entrada.strftime('%Y_%m_%d') if nueva_fecha_entrada else None,
                'entrada': entrada_con_fecha,
                'data': resultado_json
            })
    
    return datos
