import re
import os
from typing import Dict, Any, List
from datetime import datetime
from extractor import InfoExtractorBuilder, calcular_fecha_entrada, formato_fecha_espanol

# Definiciones de campos
FIELD_DEFINITIONS = {
    'travel_departure_date': 'La fecha en que el barco salió del puerto de origen. Esta fecha nunca puede ser posterior a "travel_arrival_date". En caso de estimarla, debe calcularse en relación con "travel_arrival_date". Si el mes de salida es mayor que el mes de arribo, la fecha de salida pertenece al año anterior.  Ejemplo: Si la fecha de arribo es el 5 de febrero de 1890 (1890-02-05) y la fecha de partida es el 30 de octubre, el mes de salida (octubre) es mayor que el mes de arribo (febrero), por lo que la fecha de partida será el 30 de octubre de 1889 (1889-10-30).',
    'travel_arrival_date': 'La fecha en que el barco llegó al puerto de destino [Buenos Aires].',
    'travel_duration_value': 'null',
    'travel_duration_unit': 'null',
    'travel_arrival_moment': 'null',
    'travel_departure_port': 'El nombre del puerto desde el cual salió el barco. Siempre es el primer puerto de salida (siempre está antecedido por "puerto de salida: "), los siguientes puertos de salidas, si los hay, son puertos de escala.',
    'travel_port_of_call_list': 'Lista de objetos que describen los puertos (y opcionalmente más información como fechas de llegada o salida) en los que el barco hizo escala durante su trayecto al puerto de llegada.',
    'travel_arrival_port': 'Buenos Aires',
    'ship_type': 'El tipo de embarcación, e.g., barca, bergantín, bergantín goleta, fragata, goleta, lugre, polacra, vapor, zumaca. Abreviaturas comunes: [berg|berg gta|gta|vap]',
    'ship_name': 'El nombre propio del barco.',
    'ship_tons_capacity': 'El peso total o capacidad de carga del buque en toneladas.',
    'ship_tons_units': 'Especifica las unidades en las que está expresado las dimensiones del buque. Generalmente aparece en toneladas, pero puede aparecer también en quintales.  Abreviaturas comunes: [tons|ton]',
    'ship_flag': 'El país o nacionalidad, puede ser un gentilicio, bajo cuya bandera navega el barco. Ejemplo: bergantín "francés", vapor "español", polacra "griega", bergantin goleta paquete "oriental"',
    'master_role': 'El cargo de la persona responsable a bordo, e.g., capitán, patrón. Abreviaturas comunes: [cap.|c.]',
    'master_name': 'El nombre de la persona responsable a bordo.',
    'ship_agent_name': 'Es el nombre del consignatario del buque. La persona representante del propietario del buque en un puerto. Nunca aparece en La Prensa. Su valor por defecto es "null"',
    'crew_number': 'null',
    'broker_name': 'Nombre del agente de carga, responsable de facilitar la entrega de las mercancías transportadas. En los registros, suele ubicarse entre el nombre del capitán y el del primer destinatario de la mercancía. Normalmente está precedido por el carácter "á" y seguido por la expresión "con: á" o simplemente "á". Por ejemplo: "cap Eddes á E. Norton con: á Bemberg C. 5 fds...". En este caso, "E. Norton" corresponde al agente de carga.',
    'cargo_list': 'Lista de objetos que describen las mercancías y sus respectivos dueños o destinatarios. Cada destinatario está asociado únicamente con las mercancías listadas inmediatamente después de su nombre (cuando en lugar del nombre dice "al mismo" va el nombre del broker_name; ejemplo: "á Caleri con: al mismo 540 pipas" -> "al mismo"=="Caleri"). El destinatario siempre aparece a la izquierda, seguido de las mercancías correspondientes a la derecha. Ignorar el uso de la palabra "con", ya que no representa un atributo de las mercancías. Si la mercancía es dinero, la cantidad debe corresponder al valor monetario, no al contenedor. Por ejemplo, la expresión "Ferrero 2 cj con: 3,000 dólares 15 btos papel 917 rieles 679 btos fierro" debe interpretarse como: { "cargo_merchant_name": Ferrero, "cargo": [ { "cargo_quantity": [1000], "cargo_unit": null, "cargo_commodity": "dólares" }, { "cargo_quantity": [7], "cargo_unit": "btos", "cargo_commodity": "papel" }, { "cargo_quantity": [345], "cargo_unit": null, "cargo_commodity": "rieles" }, { "cargo_quantity": [679], "cargo_unit": "btos", "cargo_commodity": "fierro" } ] }; la expresión "Ratto con: al mismo 60112 12014 vino tinto, 4014 vino blanco" debe interpretarse como: { "cargo_merchant_name": al mismo, "cargo": [ { "cargo_quantity": [60112, 12014], "cargo_unit": null, "cargo_commodity": "vino tinto" }, { "cargo_quantity": [4014], "cargo_unit": null, "cargo_commodity": "vino blanco" } ] }. Si por alguna razón la cantidad (cargo_quantity) tiene dos magnitudes consecutivas antes de la mercancía (cargo_commodity), se debe registrar las dos magnitudes (Ejemplo: "á Ferreira con: 2512 9814 vino tinto." -> cargo_list": [{"cargo_merchant_name": "Ferreira", "cargo": [{"cargo_quantity": [2512, 9814], "cargo_unit": null, "cargo_commodity": "vino tinto"}]}]). Cada objeto en la lista debe seguir esta estructura (en este orden): {"cargo_merchant_name": "Nombre del destinatario de la carga", "cargo": [{"cargo_quantity": array de números, "cargo_unit": "unidad (barricas|barriles|bocoys|bolsas|bordelesas|bultos|btos|cajas|cj|cjs|cascos|casc|cueros|cs|fardos|fds|kilos|latas|litros|pipas|pip|toneles)", "cargo_commodity": "tipo de mercancía"}]}. Es común que se utilice la palabra "id" o "idem" para referirse a la unidad o mercancía inmediatamente anterior, evitando la repetición. Puede ocurrir que tanto el valor de la clave "cargo_unit" como de la clave "cargo_commodity" sea id. Ejemplo: "Coneh y Levy id id". Si el número de la carga (cargo_quantity) es ilegible o no está presente, debe asignarse un valor de 0 (ejemplo: "Coneh y Levy id id"). Ejemplo de texto aprocesar: "á Zimermmann y ca., 1 cajon mercancias, á Nicholson Green y ca., 29 cajones mercancias, 1 id muestras, á Corach y Mora id id, 1 id cristales". Ejemplo extracción de datos: [{"cargo_merchant_name": "Zimermmann y ca.", "cargo": [{"cargo_quantity": [1], "cargo_unit": "cajon", "cargo_commodity": "mercancias"}]}, {"cargo_merchant_name": "Nicholson Green y ca.", "cargo": [{"cargo_quantity": [29], "cargo_unit": "cajones", "cargo_commodity": "mercancias"}, {"cargo_quantity": [1], "cargo_unit": "id", "cargo_commodity": "muestras"}]}, {"cargo_merchant_name": "Corach y Mora", "cargo": [{"cargo_quantity": [0], "cargo_unit": "id", "cargo_commodity": "id"}, {"cargo_quantity": [1], "cargo_unit": "id", "cargo_commodity": "cristales"}]}]. Hay mercancías (cargo_commodity) que no explicitan unidades, por ejemplo "baldosas" o "rieles", o si existe no fueron explicitadas (ejemplo: "2945 vino tinto"); en estos casos en "cargo_unit" va "null" y en "cargo_commodity" va "baldosas" o "rieles" o "vino tinto". Cuando la entrada especifica una cantidad y únicamente un identificador (en lugar de dos, como sería esperado para unidad y mercancía), se debe duplicar el identificador para asignarlo tanto a la unidad como a la mercancía. Ejemplo: "Thompson 75 cjs tejidos; Stokes 9 id" -> {"cargo_merchant_name": "Thompson", "cargo": [{"cargo_quantity": [75], "cargo_unit": "cjs", "cargo_commodity": "tejidos"}]}, {"cargo_merchant_name": "Stokes", "cargo": [{"cargo_quantity": [9], "cargo_unit": "id", "cargo_commodity": "id"}]}. Cuando la entrada NO especifica una unidad el valor por defecto es "null" (Ejemplo: "3 btos papel 7 rieles 9 btos fierro" -> "{ "cargo_quantity": [3], "cargo_unit": "btos", "cargo_commodity": "papel" }, { "cargo_quantity": [7], "cargo_unit": null, "cargo_commodity": "rieles" }, { "cargo_quantity": [9], "cargo_unit": "btos", "cargo_commodity": "fierro" }". Cuando una mercancía está antecedida por dos cantidades y dos unidades, las cantidades van en un array [1, 2] y las unidades superadas por punto y coma "cj; casc" (ejemplo: "15 cj 5 casc provisiones" -> "{ "cargo_quantity": [15, 5], "cargo_unit": "cj; casc", "cargo_commodity": "provisiones" } "). Los pasajeros nunca van como mercancías.',
    'passengers': 'Representa la cantidad total de pasajeros.',
    'in_ballast': 'Define si se menciona que la embarcación está "en lastre" [True | False]',
    'quarantine': 'Información relativa a la existencia de condiciones especiales de la llegada motivadas por circunstancias sanitarias que imponen la cuarentena.',
    'forced_arrival': 'Información sobre la llegada al puerto debido a causas imprevistas, como un arribo forzoso por temporal, avería u otras emergencias.',
    'obs': 'Notas o comentarios adicionales que aborden aspectos no contemplados en las variables registradas, proporcionando información contextual o relevante sobre el evento.'
}

# Template del JSON
JSON_TEMPLATE = {
    'travel_departure_date': None,
    'travel_arrival_date': None,
    'travel_duration_value': None,
    'travel_duration_unit': None,
    'travel_arrival_moment': None,
    'travel_departure_port': None,
    'travel_port_of_call_list': [],
    'travel_arrival_port': None,
    'ship_type': None,
    'ship_name': None,
    'ship_tons_capacity': None,
    'ship_tons_units': None,
    'ship_flag': None,
    'master_role': None,
    'master_name': None,
    'ship_agent_name': None,
    'crew_number': None,
    'broker_name': None,
    'cargo_list': [],
    'passengers': None,
    'in_ballast': None,
    'quarantine': None,
    'forced_arrival': None,
    'obs': None
}

# Ejemplos
EXAMPLES = """EJEMPLO 1: 
  input = 'Fecha de arribo: 4 de enero de 1880; puerto de salida: Pernambuco el 23 de Dbre berg gta portugues Gomez de Castro 147 tons cap Goncalvez à J Cibils con: 40 pip caña, 50 bcas azúcar moscavada 975 bcas 75 1[4 azúcar blanca; á G Schiano 1 baul, 1 balija alhajas.' 
  output = '{ "travel_departure_date": "1879-12-23", "travel_arrival_date": "1880-01-04", "travel_duration_value": null, "travel_duration_unit": null, "travel_arrival_moment": null, "travel_departure_port": "Pernambuco", "travel_port_of_call_list": [], "travel_arrival_port": "Buenos Aires", "ship_type": "berg gta", "ship_name": "Gomez de Castro", "ship_tons_capacity":  147, "ship_tons_units": " tons", "ship_flag": "portugues", "master_role": "cap", "master_name": "Goncalvez", "ship_agent_name": null, "crew_number": null, "broker_name": "J Cibils", "cargo_list": [ { "cargo_merchant_name": "J Cibils", "cargo": [ { "cargo_quantity": [40], "cargo_unit": "pip", "cargo_commodity": "caña" }, { "cargo_quantity": [50], "cargo_unit": "bcas", "cargo_commodity": "azúcar moscavada" }, { "cargo_quantity": [975], "cargo_unit": "bcas", "cargo_commodity": "azúcar blanca" } ] }, { "cargo_merchant_name": "G Schiano", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "baul", "cargo_commodity": null }, { "cargo_quantity": [1], "cargo_unit": "balija", "cargo_commodity": "alhajas" } ] } ], "passengers": null, "in_ballast": false, "quarantine": null, "forced_arrival": null, "obs": "75 1[4" }'
  EJEMPLO 2: 
  input = 'Fecha de arribo: 5 de enero de 1880; puerto de salida: Londres Amberes Rio Janeiro y Montevido vapor inglés Horrox 1101 tons cap Eddes á E, Norton con: á Bemberg C. 5 fds bsas 1 bto mtras; J Fulton 15 cj 5 casc provisiones; Parry 115 cj merc. J. Etchegaray 10 fds medias; Tramway Ciudad de Buenos Aires 25 casc herraduras; H. Peltzer 10 cj drogas; Puerto Ensenada 24 btos acero; Ferro C, del Sud 6 cj cristaleria; Moore C.12 cj perfumeria, Hape hnos 6 fds bolsas; Orden 230 cj hojalata 331 bto merc 51 cj id 9 id papel.' 
  output = '{ "travel_departure_date": null, "travel_arrival_date": "1880-01-05", "travel_duration_value": null, "travel_duration_unit": null, "travel_arrival_moment": null, "travel_departure_port": "Londres", "travel_port_of_call_list": [ { "port_of_call_place": "Amberes", "port_of_call_arrival_date": null, "port_of_call_departure_date": null }, { "port_of_call_place": " Rio Janeiro", "port_of_call_arrival_date": null, "port_of_call_departure_date": null }, { "port_of_call_place": " Montevideo", "port_of_call_arrival_date": null, "port_of_call_departure_date": null } ], "travel_arrival_port": "Buenos Aires", "ship_type": "vapor", "ship_name": "Horrox", "ship_tons_capacity": 1101, "ship_tons_units": "tons", "ship_flag": "inglés", "master_role": "cap", "master_name": "Eddes", "ship_agent_name": null, "crew_number": null, "broker_name": "E. Norton", "cargo_list": [ { "cargo_merchant_name": "Bemberg C.", "cargo": [ { "cargo_quantity": [5], "cargo_unit": "fds", "cargo_commodity": "bsas" }, { "cargo_quantity": [1], "cargo_unit": "bto", "cargo_commodity": "mtras" } ] }, { "cargo_merchant_name": "J Fulton", "cargo": [ { "cargo_quantity": [15, 5], "cargo_unit": "cj; casc", "cargo_commodity": "provisiones" } ] }, { "cargo_merchant_name": "Parry", "cargo": [ { "cargo_quantity": [115], "cargo_unit": "cj", "cargo_commodity": "merc." } ] }, { "cargo_merchant_name": "J. Etchegaray", "cargo": [ { "cargo_quantity": [10], "cargo_unit": "fds", "cargo_commodity": "medias" } ] }, { "cargo_merchant_name": "Tramway Ciudad de Buenos Aires", "cargo": [ { "cargo_quantity": [25], "cargo_unit": "casc", "cargo_commodity": "herraduras" } ] }, { "cargo_merchant_name": "H. Peltzer", "cargo": [ { "cargo_quantity": [10], "cargo_unit": "cj", "cargo_commodity": "drogas" } ] }, { "cargo_merchant_name": "Puerto Ensenada", "cargo": [ { "cargo_quantity": [24], "cargo_unit": "btos", "cargo_commodity": "acero" } ] }, { "cargo_merchant_name": "Ferro C. del Sud", "cargo": [ { "cargo_quantity": [6], "cargo_unit": "cj", "cargo_commodity": "cristaleria" } ] }, { "cargo_merchant_name": "Moore C.", "cargo": [ { "cargo_quantity": [12], "cargo_unit": "cj", "cargo_commodity": "perfumeria" } ] }, { "cargo_merchant_name": "Hape hnos", "cargo": [ { "cargo_quantity": [6], "cargo_unit": "fds", "cargo_commodity": "bolsas" } ] }, { "cargo_merchant_name": "Orden", "cargo": [ { "cargo_quantity": [230], "cargo_unit": "cj", "cargo_commodity": "hojalata" }, { "cargo_quantity": [331], "cargo_unit": "bto", "cargo_commodity": "merc" }, { "cargo_quantity": [51], "cargo_unit": "cj", "cargo_commodity": "id" }, { "cargo_quantity": [9], "cargo_unit": "id", "cargo_commodity": "papel" } ] }], "quarantine": null, "forced_arrival": null, "obs": null }'
  EJEMPLO 3: 
  input = 'Fecha de arribo: 11 de enero de 1880; puerto de salida: Amberes à M. del Pont 51 cj velas; W. Paats 200 cj quesos; F F. 200 cj ginebra; F. Meyer 2 casc vino; H. Koch 58 cj manufacturas; Bemberg C. 36 fds papel; C. Riva 20 btos quesos; J, Lopez 1 cj armas; Verney C, 23 id id, A, Bunge 1 id vino; L, Logegaray 26 id 6 barriles ferreteria; Mallman C. 8 fds lana 1 bto mtras: F. Chás é hijos 61 id cristaleria C. F. Bally 30 id calzado; J. Cadmus 2 cj con: 100,000 francos 15 btos papel 917 rieles 679 btos fierro.' 
  output = '{ "travel_departure_date": null, "travel_arrival_date": "1880-01-11", "travel_duration_value": null, "travel_duration_unit": null, "travel_arrival_moment": null, "travel_departure_port": "Amberes", "travel_port_of_call_list": [], "travel_arrival_port": "Buenos Aires", "ship_type": null, "ship_name": null, "ship_tons_capacity": null, "ship_tons_units": null, "ship_flag": null, "master_role": null, "master_name": null, "ship_agent_name": null, "crew_number": null, "broker_name": null , "cargo_list": [ { "cargo_merchant_name": "M. del Pont", "cargo": [ { "cargo_quantity": [51], "cargo_unit": "cj", "cargo_commodity": "velas" } ] }, { "cargo_merchant_name": "W. Paats", "cargo": [ { "cargo_quantity": [200], "cargo_unit": "cj", "cargo_commodity": "quesos" } ] }, { "cargo_merchant_name": "F F.", "cargo": [ { "cargo_quantity": [200], "cargo_unit": "cj", "cargo_commodity": "ginebra" } ] }, { "cargo_merchant_name": "F. Meyer", "cargo": [ { "cargo_quantity": [2], "cargo_unit": "casc", "cargo_commodity": "vino" } ] }, { "cargo_merchant_name": "H. Koch", "cargo": [ { "cargo_quantity": [58], "cargo_unit": "cj", "cargo_commodity": "manufacturas" } ] }, { "cargo_merchant_name": "Bemberg C.", "cargo": [ { "cargo_quantity": [36], "cargo_unit": "fds", "cargo_commodity": "papel" } ] }, { "cargo_merchant_name": "C. Riva", "cargo": [ { "cargo_quantity": [20], "cargo_unit": "btos", "cargo_commodity": "quesos" } ] }, { "cargo_merchant_name": "J. Lopez", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "cj", "cargo_commodity": "armas" } ] }, { "cargo_merchant_name": "Verney C.", "cargo": [ { "cargo_quantity": [23], "cargo_unit": "id", "cargo_commodity": "id" } ] }, { "cargo_merchant_name": "A. Bunge", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "id", "cargo_commodity": "vino" } ] }, { "cargo_merchant_name": "L. Logegaray", "cargo": [ { "cargo_quantity": [26], "cargo_unit": "id", "cargo_commodity": "id" }, { "cargo_quantity": [6], "cargo_unit": "barriles", "cargo_commodity": "ferreteria" } ] }, { "cargo_merchant_name": "Mallman C.", "cargo": [ { "cargo_quantity": [8], "cargo_unit": "fds", "cargo_commodity": "lana" }, { "cargo_quantity": [1], "cargo_unit": "bto", "cargo_commodity": "mtras" } ] }, { "cargo_merchant_name": "F. Chás é hijos", "cargo": [ { "cargo_quantity": [61], "cargo_unit": "id", "cargo_commodity": "cristaleria" } ] }, { "cargo_merchant_name": "C. F. Bally", "cargo": [ { "cargo_quantity": [30], "cargo_unit": "id", "cargo_commodity": "calzado" } ] }, { "cargo_merchant_name": "J. Cadmus", "cargo": [ { "cargo_quantity": [100000], "cargo_unit": null, "cargo_commodity": "francos" }, { "cargo_quantity": [15], "cargo_unit": "btos", "cargo_commodity": "papel" }, { "cargo_quantity": [917], "cargo_unit": null, "cargo_commodity": "rieles" }, { "cargo_quantity": [679], "cargo_unit": "btos", "cargo_commodity": "fierro" } ] } ], "passengers": null, "in_ballast": null, "quarantine": null, "forced_arrival": null, "obs": null }'
  EJEMPLO 4: 
  input = ''Fecha de arribo: 1 de marzo de 1880; puerto de salida: Montevideo vapor inglés Saturno 200 tons cap Magnasco á P Risso con: á F Uriburu 1 cj mercs; S Biecker 9 barr vacios; B Iruol 1 paq pfts 120; Carlisle C 1 id encoms; F de las Carreras 1 fdo id de tránsito para el Uruguay 238 btos mercs.' 
  output = '{ "travel_departure_date": null, "travel_arrival_date": "1880-03-01", "travel_duration_value": null, "travel_duration_unit": null, "travel_arrival_moment": null, "travel_departure_port": "Montevideo", "travel_port_of_call_list": [], "travel_arrival_port": "Buenos Aires", "ship_type": "vapor", "ship_name": "Saturno", "ship_tons_capacity": 200, "ship_tons_units": tons, "ship_flag": "inglés", "master_role": "cap", "master_name": "Magnasco", "ship_agent_name": null, "crew_number": null, "broker_name": "P Risso" , "cargo_list": [ { "cargo_merchant_name": "F Uriburu", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "cj", "cargo_commodity": "mercs" } ] }, { "cargo_merchant_name": "S Biecker", "cargo": [ { "cargo_quantity": [9], "cargo_unit": "barr", "cargo_commodity": "vacios" } ] }, { "cargo_merchant_name": "B Iruol", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "paq", "cargo_commodity": "120 pfts" } ] }, { "cargo_merchant_name": "Carlisle C", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "id", "cargo_commodity": "encoms" } ] }, { "cargo_merchant_name": "F de las Carreras", "cargo": [ { "cargo_quantity": [1], "cargo_unit": "fdo", "cargo_commodity": "id" } ] }, { "cargo_merchant_name": "de tránsito para el Uruguay", "cargo": [ { "cargo_quantity": [238], "cargo_unit": "btos", "cargo_commodity": "mercs" } ] } ], "passengers": null, "in_ballast": null, "quarantine": null, "forced_arrival": null, "obs": null }'"""

# Configuración
MODELO = "gpt-4o-mini"

# Configuración del schema JSON
JSON_SCHEMA = {
  "type": "json_schema",
  "json_schema": {
    "name": "ship_entry",
    "strict": True,
    "schema": {
      "type": "object",
      "properties": {
        "travel_departure_date": {
          "type": "string",
          "description": "Fecha de salida del puerto en formato YYYY-MM-DD.",
          "nullable": True
        },
        "travel_arrival_date": {
          "type": "string",
          "description": "Fecha de llegada al puerto en formato YYYY-MM-DD.",
          "nullable": True
        },
        "travel_duration_value": {
          "type": "string",
          "description": "null",
          "nullable": True
        },
        "travel_duration_unit": {
          "type": "string",
          "description": "null",
          "nullable": True
        },
        "travel_arrival_moment": {
          "type": "string",
          "description": "null",
          "nullable": True
        },
        "travel_departure_port": {
          "type": "string",
          "description": "Puerto desde el cual salió el barco.",
          "nullable": True
        },
        "travel_port_of_call_list": {
          "type": "array",
          "description": "Lista de puertos donde el barco hizo escala.",
          "nullable": True,
          "items": {
            "type": "object",
            "properties": {
              "port_of_call_place": {
                "type": "string",
                "description": "Puerto donde hizo la escala.",
                "nullable": True
              },
              "port_of_call_arrival_date": {
                "type": "string",
                "description": "Fecha de llegada al puerto de escala.",
                "nullable": True
              },
              "port_of_call_departure_date": {
                "type": "string",
                "description": "null",
                "nullable": True
              },
            },
            "required": ["port_of_call_place", "port_of_call_arrival_date", "port_of_call_departure_date"],
            "additionalProperties": False
          },
        },
        "travel_arrival_port": {
          "type": "string",
          "description": "Buenos Aires",
          "nullable": True
        },
        "ship_type": {
          "type": "string",
          "description": "Tipo de embarcación.",
          "nullable": True
        },
        "ship_name": {
          "type": "string",
          "description": "Nombre del barco.",
          "nullable": True
        },
        "ship_tons_capacity": {
          "type": "number",
          "description": "Capacidad de carga del buque en toneladas.",
          "nullable": True
        },
        "ship_tons_units": {
          "type": "string",
          "description": "Especifica las unidades en las que está expresado las dimensiones del buque",
          "nullable": True
        },
        "ship_flag": {
          "type": "string",
          "description": "País o nacionalidad bajo cuya bandera navega el barco. Ejemplo: 'oriental'",
          "nullable": True
        },
        "master_role": {
          "type": "string",
          "description": "Cargo del responsable a bordo.",
          "nullable": True
        },
        "master_name": {
          "type": "string",
          "description": "Nombre del responsable a bordo.",
          "nullable": True
        },
        "ship_agent_name": {
          "type": "string",
          "description": "null",
          "nullable": True
        },
        "crew_number": {
          "type": "string",
          "description": "null",
          "nullable": True
        },
        "broker_name": {
          "type": "string",
          "description": "Nombre del agente marítimo.",
          "nullable": True
        },
        "cargo_list": {
          "type": "array",
          "description": "Lista de mercancías transportadas y sus propietarios.",
          "nullable": True,
          "items": {
            "type": "object",
            "properties": {
              "cargo_merchant_name": {
                "type": "string",
                "description": "Es el propietario de la carga o aquella persona a quien dicha carga va destinada.",
                "nullable": True
              },
              "cargo": {
                "type": "array",
                "description": "Lista de mercancías transportadas.",
                "nullable": True,
                "items": {
                  "type": "object",
                  "properties": {
                    "cargo_quantity": {
                      "type": "array",
                      "description": "Representa la cantidad total de la carga en forma numérica. Si el número es ilegible o no está presente, debe asignarse un valor de 0.",
                      "nullable": True
                    },
                    "cargo_unit": {
                      "type": "string",
                      "description": "Expresa las unidades de medida en las que la carga aparece. Ejemplo: 'cargo_unit': 'cj', 'cargo_unit': 'id'",
                      "nullable": True
                    },
                    "cargo_commodity": {
                      "type": "string",
                      "description": "Expresa los distintos productos o tipos de mercancías que transporta el buque. Ejemplo: 'cargo_commodity': 'cristales', 'cargo_unit': 'id'",
                      "nullable": True
                    }
                  },
                  "required": ["cargo_quantity", "cargo_unit", "cargo_commodity"],
                  "additionalProperties": False
                }
              }
            },
            "required": ["cargo_merchant_name", "cargo"],
            "additionalProperties": False
          }
        },
        "passengers": {
          "type": "number",
          "description": "Representa la cantidad total de pasajeros.",
          "nullable": True
        },
        "in_ballast": {
          "type": "boolean",
          "description": "Define si se menciona que la embarcación está 'en lastre' [True | False]",
          "nullable": True
        },
        "quarantine": {
          "type": "string",
          "description": "Información relativa a la existencia de condiciones especiales de la llegada motivadas por circunstancias sanitarias que imponen la cuarentena.",
          "nullable": True
        },
        "forced_arrival": {
          "type": "string",
          "description": "Información sobre la llegada al puerto debido a causas imprevistas, como un arribo forzoso por temporal, avería u otras emergencias.",
          "nullable": True
        },
        "obs": {
          "type": "string",
          "description": "Notas o comentarios adicionales que aborden aspectos no contemplados en las variables registradas, proporcionando información contextual o relevante sobre el evento.",
          "nullable": True
        }
      },
      "required": [
        "travel_departure_date", 
        "travel_arrival_date",
        "travel_duration_value", 
        "travel_duration_unit",
        "travel_arrival_moment",
        "travel_departure_port", 
        "travel_port_of_call_list", 
        "travel_arrival_port",
        "ship_type", 
        "ship_name", 
        "ship_tons_capacity", 
        "ship_tons_units",
        "ship_flag",
        "master_role", 
        "master_name", 
        "ship_agent_name",
        "crew_number",
        "broker_name",
        "cargo_list",
        "passengers",
        "in_ballast",
        "quarantine",
        "forced_arrival",
        "obs"
      ],
      "additionalProperties": False
    }
  }
}

MODEL_CONFIG = {
    "temperature": 0,
    "max_tokens": 9000,
    "top_p": 0,
    "frequency_penalty": 0,
    "presence_penalty": 0
}

MESSAGES_CONFIG = {
    "system": {
        "role": "system",
        "content": (
            "Eres un asistente experto en extraer información estructurada de notas sobre entradas de barcos a puerto. "
            "Debes responder EXCLUSIVAMENTE con un objeto JSON válido que contenga los campos solicitados. "
            "Si no encuentras información para algún campo, debes responder con el valor null en ese campo."
        )
    },
    "template": {
        "role": "user",
        "content": (
            "Extrae la siguiente información del evento de entrada de barco descrito en la nota, "
            "utilizando el formato JSON exacto: {json_template}. "
            "Aquí está la definición de cada clave: {field_definitions} "
            "Ejemplo de nota: {input_example}"
            "Texto de la nota: {input_text}"
        )
    }
}

def dividir_texto_maritimo(texto):
    # Eliminar "MARITIMA." inicial si está presente y limpiar \n iniciales
    texto = re.sub(r'^MARITIMA\.\s*|^MARITIMA-|^MARITIMA\s', '', texto, flags=re.MULTILINE)
    texto = texto.lstrip()
    
    # Definir los patrones para dividir, permitiendo variaciones
    patrones = [
        r'ULTRAMAR',
        r'UITRAMAR',
        r'ULTAMAR',
        r'Ultram',
        r'MANIFIESTO',
        r'Manif',
        r'CABOTAJE',
        r'Cabota'
    ]
    
    # Combinar patrones en una sola expresión regular
    patron_combinado = '|'.join(patrones)
    
    # Encontrar todas las coincidencias de los patrones
    matches = list(re.finditer(patron_combinado, texto, re.IGNORECASE))
    
    # Si no hay coincidencias, devolver el texto completo
    if not matches:
        return [texto.strip()]
    
    # Dividir el texto en secciones principales
    resultado = []
    for i, match in enumerate(matches):
        start = match.start()
        end = matches[i+1].start() if i+1 < len(matches) else len(texto)
        seccion = texto[start:end].strip()
        if seccion:
            resultado.append(seccion)
    
    # Añadir el texto antes del primer subtítulo si existe
    if matches[0].start() > 0:
        texto_inicial = texto[:matches[0].start()].strip()
        if texto_inicial:
            resultado.insert(0, texto_inicial)
    
    return dividir_por_dias(resultado)

def dividir_por_dias(secciones):
    resultado_final = []
    for seccion in secciones:
        # Limpiar la sección de \n iniciales
        seccion = seccion.lstrip()
        
        # Identificar la categoría principal y normalizarla
        categoria_match = re.match(r'^(ULTRAMAR|Ultram|MANIFIESTO|Manif|CABOTAJE|Cabota)', seccion, re.IGNORECASE)
        if categoria_match:
            categoria_lower = categoria_match.group(1).lower()
            if 'ultram' in categoria_lower:
                categoria = 'ULTRAMAR'
            elif 'manif' in categoria_lower:
                categoria = 'MANIFIESTO'
            elif 'cabota' in categoria_lower:
                categoria = 'CABOTAJE'
        else:
            categoria = ""
        
        # Patrón para identificar días, incluyendo variaciones
        #patron_dia = r'(?:Ultramar|Cabotajo)?-?\s*DIA\s+\d+(?:\s+[yY]\s+\d+)*'
        patron_dia = r'(?:^|\n)(?:(?:Ultramar|Cabotajo)?-?(?:Dia|DIA)\s+\d+\.?)'
        
        # Dividir la sección por días
        partes = re.split(patron_dia, seccion)
        
        # Obtener los encabezados de los días
        encabezados = re.findall(patron_dia, seccion)
        
        # Procesar cada parte
        for i, parte in enumerate(partes):
            parte = parte.strip()
            if parte:
                if i == 0:
                    # Manejar el caso especial del primer segmento
                    match = re.match(r'^(?:Ultramar|Ultram|Cabotajo|MANIFIESTO).*?(?=\n|$)', parte, re.IGNORECASE)
                    if match:
                        encabezado = match.group(0)
                        contenido = parte[len(encabezado):].strip()
                        if not re.search(r'\b(?:' + '|'.join([re.escape(categoria), 'Ultram', 'Cabotajo']) + r')\b', encabezado, re.IGNORECASE):
                            resultado_final.append(f"{categoria}\n{encabezado}\n{contenido}".lstrip())
                        else:
                            resultado_final.append(f"{encabezado}\n{contenido}".lstrip())
                    else:
                        resultado_final.append(f"{categoria}\n{parte}".lstrip())
                elif i <= len(encabezados):
                    # Verificar si la categoría ya está presente en el encabezado del día
                    encabezado = encabezados[i-1].strip()
                    if not re.search(r'\b(?:ULTRAMAR|Ultram|CABOTAJE|Cabotajo|MANIFIESTO)\b', encabezado, re.IGNORECASE):
                        encabezado = f"{categoria}\n{encabezado}"
                    contenido = parte.strip()
                    resultado_final.append(f"{encabezado}\n{contenido}".lstrip())
    
    return resultado_final

def generar_etiqueta(cadena):
    cadena = cadena.lower()
    if "trama" in cadena:
        return "T"
    elif "bota" in cadena:
        return "C"
    elif "nifies" in cadena:
        return "M"
    else:
        return "E"

def obtener_dia(texto):
    match = METADATA_PATTERN.search(texto)
    if match:
        # Esto obtendrá el primer grupo no None (es decir, el que contiene el número)
        dia = next((grupo for grupo in match.groups() if grupo is not None), None)
        return dia
    return None

# Expresiones regulares
# METADATA_PATTERN = re.compile(r'^(?:ULTRAMAR(?: DIA \d+)?|Ultram(?:-Dia)?|DIA \d+|(-ULTRAMAR)?\s+DIA\s+\d+(?:\s+[yY]\s+\d+)*Cabot.*DIA|Cabot.*Dia|MANIFIESTO)\.?\s*(?:Dia\s*(\d+)\.?|-DIA\s*(\d+)\.?|\s*(\d+)\.?)?\n?', re.MULTILINE | re.UNICODE)

# METADATA_PATTERN = re.compile(
#     r'^(?:'
#     r'(ULTRAMAR|CABOTAJE|Ultramar|Cabotaje)\s+'  # Captura "ULTRAMAR" o "CABOTAJE" en mayúsculas y minúsculas
#     r'([A-ZÁÉÍÓÚÑa-záéíóúñ]+)?\s*(\d{1,2})(?:\s+[yY]\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+)\s+(\d{1,2}°?))?'  # Fecha con mes y día, o solo día, con "Y" opcional
#     r'|DIA\s+(\d{1,2})(?:\s+[yY]\s+(\d{1,2}°?))?'  # Captura "DIA X" o "DIA X Y"
#     r'|Dia\s+(\d{1,2})'  # Captura "Dia X"
#     r'|(?:DIA|Dia)?\s*(\d{1,2}°?)(?:\s+[yY]\s+(\d{1,2}°?))?'
#     r'|([A-ZÁÉÍÓÚÑa-záéíóúñ]+)\s+(\d{1,2}°?)(?:\s+[yY]\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+)\s+(\d{1,2}°?))?'
#     r')'
#     r'(?=\s|,|-|$)',  # Asegura que coincida hasta un separador válido o el final
#     re.MULTILINE | re.UNICODE
# )

METADATA_PATTERN = re.compile(
    r'^(?:ULTRAMAR.*)?\s*(\d{1,2}?)(?:\s+[yY]\s+(\d{1,2}?))(?=\s|,|-|$)?'
    r'|'
    r'^(?:'
    r'(ULTRAMAR|CABOTAJE|Ultramar|Cabotaje)\s+'  # Captura "ULTRAMAR" o "CABOTAJE" en mayúsculas y minúsculas
    r'([A-ZÁÉÍÓÚÑa-záéíóúñ]+)?\s*(\d{1,2})(?:\s+[yY]\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+)\s+(\d{1,2}°?))?'  # Fecha con mes y día, o solo día, con "Y" opcional
    r'|DIA\s+(\d{1,2})(?:\s+[yY]\s+(\d{1,2}°?))?'  # Captura "DIA X" o "DIA X Y"
    r'|Dia\s+(\d{1,2})'  # Captura "Dia X"
    r'|(?:DIA|Dia)?\s*(\d{1,2}°?)(?:\s+[yY]\s+(\d{1,2}°?))?'
    r'|([A-ZÁÉÍÓÚÑa-záéíóúñ]+)\s+(\d{1,2}°?)(?:\s+[yY]\s+([A-ZÁÉÍÓÚÑa-záéíóúñ]+)\s+(\d{1,2}°?))?'
    r')'
    r'(?=\s|,|-|$)',  # Asegura que coincida hasta un separador válido o el final
    re.MULTILINE | re.UNICODE
)

DIA_PATTERN = re.compile(r'(\d{1,2})(?!.*\d)')
ENTRADA_PATTERN = re.compile(r'\n(?=[A-ZÁÉÍÓÚÜÑ][a-záéíóúüñ]+)')
#ENTRADA_PATTERN = re.compile(r'\n(?=[A-Z][a-z]+)')

def procesar_archivo(nombre_archivo: str, contenido: str) -> List[Dict[str, Any]]:
    """
    Procesa un archivo y extrae la información relevante.
    """
    # Paso 1: Aplicar las funciones de split para obtener los segmentos
    segmentos = dividir_texto_maritimo(contenido)
    
    datos = []
    id_counter = 1
    
    fecha_nota = nombre_archivo[:10] if len(nombre_archivo) >= 10 else ""
    nombre_prensa = nombre_archivo[15:17] if len(nombre_archivo) >= 10 else ""

    # Paso 2 y 3: Procesar cada segmento
    for segmento in segmentos:
        # Extraer metadatos del segmento
        match_segmento = METADATA_PATTERN.search(segmento)
        metadata_segmento = match_segmento.group() if match_segmento else "Metadatos no encontrados"
        
        dia_match = DIA_PATTERN.search(metadata_segmento)
        dia = dia_match.group(1) if dia_match else "" # fecha_nota[8:10]
        
        seccion = generar_etiqueta(metadata_segmento)
        
        nueva_fecha_entrada = calcular_fecha_entrada(fecha_nota, dia)
        fecha_arribo_texto = formato_fecha_espanol(nueva_fecha_entrada)
        if fecha_arribo_texto == "Fecha desconocida":
          fecha_arribo_texto = fecha_nota.replace("_", "-")
        
        contenido_limpio = re.sub(r'^' + re.escape(metadata_segmento), '', segmento, flags=re.MULTILINE).strip()
        contenido_limpio = re.sub(r'^-', '', contenido_limpio)
        entradas = ENTRADA_PATTERN.split(contenido_limpio)
        
        metadata_segmento = metadata_segmento.rstrip()
        
        extractor = InfoExtractorBuilder()\
            .with_api_key(os.environ.get("OPENAI_API_KEY"))\
            .with_model(MODELO)\
            .with_json_schema(JSON_SCHEMA)\
            .with_model_config(MODEL_CONFIG)\
            .with_field_definitions(FIELD_DEFINITIONS)\
            .with_messages_config(MESSAGES_CONFIG)\
            .with_json_template(JSON_TEMPLATE)\
            .with_examples(EXAMPLES)\
            .build()
        
        for entrada in entradas:
            if entrada.strip():
                entrada_con_fecha = f"Fecha de arribo: {fecha_arribo_texto}; puerto de salida: {entrada.strip()}"
                
                try:
                    resultado_json = extractor.extraer_informacion(entrada_con_fecha)
                except Exception as e:
                    print(f"Error al procesar la entrada con InfoExtractor: {str(e)}")
                    resultado_json = {"error": "No se pudo procesar la entrada"}
                
                datos.append({
                    'name_txt': nombre_archivo,
                    'metadata_entrada': metadata_segmento,
                    'publication_date': fecha_nota,
                    'publication_name': nombre_prensa,
                    'publication_edition': 'U',
                    'news_section': seccion,
                    'dia': dia,
                    'fecha_entrada': nueva_fecha_entrada.strftime('%Y_%m_%d') if nueva_fecha_entrada else None,
                    'entrada': entrada_con_fecha,
                    'id_entrada': id_counter,
                    'data': resultado_json
                })
                
                id_counter += 1
    
    return datos
