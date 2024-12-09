import re

# Compilar expresiones regulares
METADATA_PATTERN = re.compile(r'^(MAR.*?)(?=[A-ZÁ-Ú][a-zá-ú])', re.MULTILINE | re.UNICODE)
DIA_PATTERN = re.compile(r'(\d{1,2})(?!.*\d)')
ENTRADA_PATTERN = re.compile(r'\n(?=[A-Z][a-z]+)')
