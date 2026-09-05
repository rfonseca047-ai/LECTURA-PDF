import io
import json
import re
import os
from PIL import Image
from dotenv import load_dotenv

# Load environment variables from .env file immediately
load_dotenv()

try:
    import pymupdf
except ImportError:
    pymupdf = None

def get_internal_gemini_key():
    """Safely retrieves GEMINI_API_KEY internally."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and "GEMINI_API_KEY" in st.secrets:
            return str(st.secrets["GEMINI_API_KEY"])
    except Exception:
        pass
    return os.environ.get("GEMINI_API_KEY", "")

def convert_pdf_to_images(pdf_bytes):
    """Converts a PDF file (bytes) to a list of PIL Images using pymupdf."""
    images = []
    if pymupdf:
        doc = pymupdf.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            pix = page.get_pixmap(dpi=300)
            img_data = pix.tobytes("png")
            img = Image.open(io.BytesIO(img_data))
            images.append(img)
    else:
        img = Image.open(io.BytesIO(pdf_bytes))
        images.append(img)
    return images

def auto_orient_image(img):
    """
    Checks if image height < width (landscape/rotated) and rotates 90 degrees if needed.
    """
    w, h = img.size
    if w > h:
        return img.rotate(270, expand=True)
    return img

def extract_table_from_image_gemini(image, api_key=None):
    """
    Calls Gemini Multimodal API.
    Extracts raw handwritten data, PREDIO from title, and handwritten INCIDENCIA (VAC, INC, LIBRE, AUSENCIA).
    If no incidence note is written, adds 'PRESENTE'.
    """
    from google import genai
    from google.genai import types
    
    key = api_key or get_internal_gemini_key()
    if not key:
        err_text = "No se encontró la clave GEMINI_API_KEY en el entorno ni en el archivo .env"
        print(f"Error detectado: {err_text}")
        raise ValueError(err_text)

    client = genai.Client(api_key=key)

    prompt = """
    Actúa como un escáner OCR experto en planillas de asistencia. Este es un documento escaneado que contiene registros de asistencia con datos manuscritos a lapicero.

    TU TAREA ES TRANSCRIBIR LOS DATOS CRUDOS DE LA IMAGEN, DETECTAR EL PREDIO EN EL TÍTULO Y CAPTURAR CUALQUIER INCIDENCIA MANUSCRITA.

    1. EXAMINA EL TÍTULO DEL DOCUMENTO en la parte superior (ejemplo: 'PERSONAL AUTORIZADO A INGRESAR A PREDIO 3', 'PREDIO 1', 'PREDIO 2') e identifica el número de predio.
    2. Extrae las siguientes 7 llaves en minúscula para cada registro válido:
       - "cedula": Cédula / Código de empleado
       - "nombre": Nombre completo del empleado
       - "departamento": Departamento u Oficina
       - "hora_entrada": Hora anotada a lapicero (ej: 6:52, 06:05, 17:55, 6:55, 7:53, 05:52, 6:36, 6:45, 06:55, 05:57 o "" si está en blanco)
       - "hora_salida": Hora anotada a lapicero (ej: 18:00, 06:00, 17:05, 17:14, 17:03, 17:00, 17:02, 12:06 o "" si está en blanco)
       - "incidencia": Si en manuscrito a lapicero lleva escrito VAC, INC, LIBRE, AUSENCIA u otra nota manuscrita en la fila, transcríbela tal cual. SI NO HAY NINGUNA NOTA O ESTÁ EN BLANCO, COLOCA EXACTAMENTE 'PRESENTE'.
       - "predio": Número de predio detectado en el título (ej: 1, 2, 3). Si no se menciona explícitamente, coloca 1.

    INSTRUCCIONES CRÍTICAS:
    - REGLA CRÍTICA DE NOMBRES TACHADOS: Si el nombre de un empleado o su renglón entero está TACHADO o CANCELADO a lapicero/bolígrafo (una línea horizontal o tachadura cruzando el nombre), NO LO EXTRAIGAS. Omite a los empleados tachados por completo.
    - REGLA DE INCIDENCIA: Si no hay notas manuscritas como VAC, INC, LIBRE o AUSENCIA, la llave "incidencia" DEBE SER 'PRESENTE'.
    - Devuelve ÚNICAMENTE un arreglo JSON con los objetos de los empleados válidos (no tachados).
    - Formato exacto de cada objeto JSON:
      {
        "cedula": "702950206",
        "nombre": "FENNELL ARAYA BRITTANY",
        "departamento": "OFICINA",
        "hora_entrada": "06:52",
        "hora_salida": "",
        "incidencia": "PRESENTE",
        "predio": 3
      }
    - Transcribe fielmente las horas escritas a lapicero. Si está vacía sin trazo de lapicero, coloca "".
    """

    img_byte_arr = io.BytesIO()
    image.save(img_byte_arr, format='PNG')
    img_bytes = img_byte_arr.getvalue()

    model_name = 'models/gemini-3.6-flash'

    json_config = types.GenerateContentConfig(
        response_mime_type="application/json",
        temperature=0.0
    )

    try:
        print(f"Llamando a la API de Gemini con {model_name}...")
        chat = client.chats.create(model=model_name)
        response = chat.send_message(
            message=[
                types.Part.from_bytes(data=img_bytes, mime_type='image/png'),
                prompt
            ],
            config=json_config
        )
    except Exception as err:
        err_str = str(err)
        print(f"Error detectado en modelo {model_name}: {err_str}")
        if "429" in err_str or "quota" in err_str.lower() or "resource_exhausted" in err_str.lower():
            raise ValueError("Límite de peticiones alcanzado. Verifica que tu API Key corresponda a tu cuenta de Google AI Pro.")
        else:
            raise err

    if not response or not response.text:
        err_msg = "No se obtuvo respuesta válida de Gemini"
        print(f"Error detectado: {err_msg}")
        raise RuntimeError(err_msg)

    # VITAL DEBUG PRINT
    raw_json = response.text.replace('```json', '').replace('```', '').strip()
    print("DEBUG RAW JSON:", raw_json)

    data = json.loads(raw_json)
    
    # If wrapped inside dict (e.g., {"empleados": [...]})
    if isinstance(data, dict):
        for k, v in data.items():
            if isinstance(v, list):
                data = v
                break
        if isinstance(data, dict):
            data = [data]

    normalized_data = []
    for item in data:
        if isinstance(item, dict):
            nombre_str = str(item.get("nombre", item.get("NOMBRE", ""))).strip()
            
            # Filter out crossed-out entries if tagged
            if "TACHADO" in nombre_str.upper() or "CANCELADO" in nombre_str.upper() or "ELIMINADO" in nombre_str.upper():
                print(f"Omite empleado tachado: {nombre_str}")
                continue

            pred_val = item.get("predio", item.get("PREDIO", 1))
            try:
                pred_val = int(pred_val)
            except Exception:
                pred_val = 1
                
            inc_val = str(item.get("incidencia", item.get("INCIDENCIA", ""))).strip()
            if not inc_val:
                inc_val = "PRESENTE"

            normalized_data.append({
                "cedula": str(item.get("cedula", item.get("codigo", item.get("#", "")))),
                "nombre": nombre_str,
                "departamento": str(item.get("departamento", item.get("DEPARTAMENTO", ""))),
                "hora_entrada": str(item.get("hora_entrada", item.get("entrada", item.get("Entrada", "")))),
                "hora_salida": str(item.get("hora_salida", item.get("salida", item.get("Salida", "")))),
                "incidencia": inc_val,
                "predio": pred_val
            })

    return normalized_data

def process_pdf_document(pdf_bytes, filename="", api_key=None):
    """
    Main pipeline to process a PDF or image file and extract all table rows.
    """
    if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.tiff', '.bmp')):
        img = Image.open(io.BytesIO(pdf_bytes))
        images = [img]
    else:
        images = convert_pdf_to_images(pdf_bytes)

    all_rows = []
    for img in images:
        oriented_img = auto_orient_image(img)
        rows = extract_table_from_image_gemini(oriented_img, api_key=api_key)
        if rows:
            all_rows.extend(rows)
            
    return all_rows
