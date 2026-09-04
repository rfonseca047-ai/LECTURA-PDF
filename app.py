import streamlit as st
import pandas as pd
from datetime import datetime
import os
import io
from dotenv import load_dotenv

# Load environment variables from .env file immediately
load_dotenv()

from ocr_engine import process_pdf_document
from excel_generator import create_excel_report, save_excel_to_bytes, SPANISH_DAYS

# Page Config (No Sidebar)
st.set_page_config(
    page_title="Transportes Grant S.A. - OCR Transcripción de Planillas",
    page_icon="🚛",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Targeted CSS - Preserves Streamlit Native Widget Contrast
st.markdown("""
<style>
    /* Hide Sidebar Completely */
    [data-testid="stSidebar"] {
        display: none !important;
    }
    
    /* Top Corporate Banner Styles */
    .main-banner {
        background: linear-gradient(135deg, #1B365D 0%, #0F2342 100%);
        padding: 22px 18px;
        border-radius: 12px;
        text-align: center;
        margin-bottom: 25px;
        box-shadow: 0px 4px 12px rgba(0,0,0,0.12);
        border-bottom: 4px solid #D4AF37;
    }
    .banner-title {
        color: #FFFFFF !important;
        font-weight: 800;
        font-size: 24px;
        letter-spacing: 1px;
        margin: 5px 0 2px 0;
    }
    .banner-subtitle {
        color: #D4AF37 !important;
        font-size: 13px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    .stAlert {
        border-radius: 8px !important;
    }

    /* Large Prominent Excel Download Button */
    .stDownloadButton button {
        background: linear-gradient(135deg, #1B365D 0%, #2E7D32 100%) !important;
        color: #FFFFFF !important;
        font-size: 18px !important;
        font-weight: bold !important;
        padding: 16px 32px !important;
        border-radius: 8px !important;
        border: none !important;
        width: 100% !important;
        box-shadow: 0px 4px 12px rgba(46, 125, 50, 0.3) !important;
        transition: all 0.3s ease !important;
    }
    .stDownloadButton button:hover {
        transform: translateY(-2px);
        box-shadow: 0px 6px 16px rgba(46, 125, 50, 0.4) !important;
    }

    /* Action Buttons */
    .stButton button {
        background-color: #1B365D !important;
        color: #FFFFFF !important;
        font-weight: bold !important;
        border-radius: 6px !important;
    }
</style>
""", unsafe_allow_html=True)

# TOP CONTROL BAR: Date Picker + Predio Selector/Auto-detector Mode
col_header_date, col_header_mode = st.columns([1, 2])

with col_header_date:
    report_date = st.date_input("📅 Fecha del Reporte", value=datetime.now())

with col_header_mode:
    scan_mode = st.selectbox(
        "🏢 Modo de Escaneo / Asignación de Predio",
        options=[
            "🤖 Detección Automática por Título (Escanear Todos los Predios a la Vez)",
            "🏢 Forzar Predio 1",
            "🏢 Forzar Predio 2",
            "🏢 Forzar Predio 3"
        ],
        index=0,
        help="Selecciona Detección Automática para escanear varios documentos de distintos predios al mismo tiempo (leyendo el número en el título del documento)."
    )

# Spanish Day Name Calculation
day_name = SPANISH_DAYS[report_date.weekday()]
date_formatted = report_date.strftime("%Y-%m-%d")

# Banner Title formatting
if "Predio 1" in scan_mode:
    banner_predio_text = "PREDIO 1"
elif "Predio 2" in scan_mode:
    banner_predio_text = "PREDIO 2"
elif "Predio 3" in scan_mode:
    banner_predio_text = "PREDIO 3"
else:
    banner_predio_text = "TODOS LOS PREDIOS (DETECCIÓN AUTOMÁTICA EN TÍTULO)"

st.markdown(f"""
<div class="main-banner">
    <div style="font-size: 38px; line-height: 1;">🚛</div>
    <div class="banner-title">TRANSPORTES GRANT S.A. — {banner_predio_text}</div>
    <div class="banner-subtitle">Escáner OCR de Caligrafía & Transcripción Multidocumento</div>
</div>
""", unsafe_allow_html=True)

# FILE UPLOADER SECTION
uploaded_files = st.file_uploader(
    "Cargar Documentos PDF o Imágenes Escaneadas (Puedes subir varios predios a la vez)",
    type=["pdf", "png", "jpg", "jpeg"],
    accept_multiple_files=True,
    help="Arrastra aquí todos los archivos escaneados de los Predios 1, 2 o 3."
)

if "parsed_rows" not in st.session_state:
    st.session_state["parsed_rows"] = []

if "has_processed" not in st.session_state:
    st.session_state["has_processed"] = False

if uploaded_files:
    if st.button("🚀 Transcribir Documentos con IA", use_container_width=True):
        print("Iniciando procesamiento...")
        all_extracted = []
        progress_bar = st.progress(0)
        status_text = st.empty()

        try:
            for idx, file_obj in enumerate(uploaded_files):
                status_text.info(f"Escaneando archivo {file_obj.name} ({idx+1}/{len(uploaded_files)})...")
                file_bytes = file_obj.read()
                
                rows = process_pdf_document(
                    file_bytes,
                    filename=file_obj.name
                )
                
                if rows:
                    all_extracted.extend(rows)
                
                progress_bar.progress((idx + 1) / len(uploaded_files))
                
            st.session_state["parsed_rows"] = all_extracted
            st.session_state["has_processed"] = True
            
            if all_extracted:
                status_text.success(f"¡Planillas procesadas correctamente! Se leyeron {len(all_extracted)} empleados.")
            else:
                status_text.warning("⚠️ No se leyeron registros del archivo PDF. Puedes ingresar los datos directamente en la tabla a continuación.")

        except Exception as e:
            err_msg = str(e)
            print(f"Error detectado: {err_msg}")
            if "Límite de peticiones alcanzado" in err_msg:
                st.error("⚠️ Límite de peticiones alcanzado. Verifica que tu API Key corresponda a tu cuenta de Google AI Pro.")
            else:
                st.error(f"Error de ejecución: {err_msg}")

# Interactive 9-Column Data Table & Excel Download Section
if st.session_state["has_processed"] or st.session_state["parsed_rows"]:
    st.markdown("---")
    st.subheader("🔍 Vista Previa y Edición de Datos Transcritos")
    st.info("Revisa y corrige cualquier dato en la tabla de 9 columnas antes de descargar el archivo Excel final.")
    
    raw_data = st.session_state["parsed_rows"]
    if not raw_data:
        raw_data = [{
            'cedula': '',
            'nombre': '',
            'departamento': '',
            'hora_entrada': '',
            'hora_salida': '',
            'incidencia': '',
            'predio': 1
        }]

    # Determine forced predio if specified by user
    if "Forzar Predio 1" in scan_mode:
        forced_predio = 1
    elif "Forzar Predio 2" in scan_mode:
        forced_predio = 2
    elif "Forzar Predio 3" in scan_mode:
        forced_predio = 3
    else:
        forced_predio = None  # Auto-detected per document title header!

    # Build 9-Column DataFrame Structure matching user image:
    # FECHA | Dia | # | INCIDENCIA | PREDIO | NOMBRE | DEPARTAMENTO | Entrada | Salida
    rows_for_df = []
    for item in raw_data:
        code = str(item.get("#", item.get("cedula", item.get("codigo", "")))).strip()
        inc = str(item.get("INCIDENCIA", item.get("incidencia", ""))).strip()
            
        detected_p = item.get("predio", item.get("PREDIO", 1))
        try:
            detected_p = int(detected_p)
        except Exception:
            detected_p = 1

        final_predio = forced_predio if forced_predio is not None else detected_p
        
        nombre = str(item.get("NOMBRE", item.get("nombre", ""))).strip()
        depto = str(item.get("DEPARTAMENTO", item.get("departamento", ""))).strip()
        ent = str(item.get("Entrada", item.get("hora_entrada", item.get("entrada", "")))).strip()
        sal = str(item.get("Salida", item.get("hora_salida", item.get("salida", "")))).strip()

        rows_for_df.append({
            "FECHA": date_formatted,
            "Dia": day_name,
            "#": code,
            "INCIDENCIA": inc,
            "PREDIO": final_predio,
            "NOMBRE": nombre,
            "DEPARTAMENTO": depto,
            "Entrada": ent,
            "Salida": sal
        })

    df_display = pd.DataFrame(rows_for_df)

    # 9-Column Interactive Data Editor
    edited_df = st.data_editor(
        df_display,
        num_rows="dynamic",
        use_container_width=True,
        column_config={
            "FECHA": st.column_config.TextColumn("FECHA", required=True),
            "Dia": st.column_config.TextColumn("Dia", required=True),
            "#": st.column_config.TextColumn("#", required=True),
            "INCIDENCIA": st.column_config.TextColumn("INCIDENCIA", default=""),
            "PREDIO": st.column_config.NumberColumn("PREDIO", min_value=1, max_value=20, default=1),
            "NOMBRE": st.column_config.TextColumn("NOMBRE", required=True),
            "DEPARTAMENTO": st.column_config.TextColumn("DEPARTAMENTO"),
            "Entrada": st.column_config.TextColumn("Entrada"),
            "Salida": st.column_config.TextColumn("Salida")
        }
    )
    
    recalculated_rows = edited_df.to_dict(orient="records")

    # Summary Metrics
    tot_rows = len(recalculated_rows)
    with_ent = sum(1 for r in recalculated_rows if str(r.get("Entrada", "")).strip())
    with_sal = sum(1 for r in recalculated_rows if str(r.get("Salida", "")).strip())
    with_inc = sum(1 for r in recalculated_rows if str(r.get("INCIDENCIA", "")).strip())
    
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Total Empleados Transcritos", tot_rows)
    m2.metric("Con Hora de Entrada", with_ent)
    m3.metric("Con Hora de Salida", with_sal)
    m4.metric("Con Incidencia (VAC, INC, etc.)", with_inc)

    st.markdown("---")
    
    # PROMINENT EXCEL DOWNLOAD (9 COLUMNS)
    st.subheader("📊 Descargar Base de Datos Excel")
    st.markdown("Genera el libro `.xlsx` con el diseño oficial de 9 columnas de Transportes Grant S.A.")
    
    wb = create_excel_report(recalculated_rows, date_val=report_date)
    excel_bytes = save_excel_to_bytes(wb)
    
    file_name = f"Planilla_Transportes_Grant_{date_formatted}.xlsx"
    
    st.download_button(
        label="📥 DESCARGAR BASE DE DATOS EXCEL (.XLSX)",
        data=excel_bytes,
        file_name=file_name,
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        use_container_width=True
    )

    # RESET BUTTON FOR NEW PROCESS
    st.markdown("---")
    if st.button("🔄 PROCESAR NUEVA PLANILLA", use_container_width=True):
        st.session_state["parsed_rows"] = []
        st.session_state["has_processed"] = False
        st.rerun()
