import re
from datetime import datetime, time

def clean_time_str(val):
    """Normalizes time string into HH:MM or returns empty string if blank/invalid/0:00."""
    if not val:
        return ""
    val_str = str(val).strip()
    if val_str in ["0:00", "00:00", "0", "-", "N/A", "n/a", "None", "nan"]:
        return ""
    
    match = re.search(r'(\d{1,2})[:\.](\d{2})', val_str)
    if match:
        h = int(match.group(1))
        m = int(match.group(2))
        if 0 <= h <= 23 and 0 <= m <= 59:
            return f"{h:02d}:{m:02d}"
    return ""

def parse_time_obj(time_str):
    """Converts HH:MM string to time object or None."""
    cleaned = clean_time_str(time_str)
    if not cleaned:
        return None
    try:
        parts = cleaned.split(":")
        return time(int(parts[0]), int(parts[1]))
    except ValueError:
        return None

def get_expected_start_time(departamento="", predio=1, entry_time=None):
    """
    Returns expected entry time object based on schedule matrix per Predio.
    """
    dept_upper = str(departamento).upper().strip().replace("_", " ")
    
    # PREDIO 3 SPECIFIC SCHEDULES
    if predio == 3:
        if "ZF TALLER" in dept_upper or "ZF" in dept_upper or "TALLER" in dept_upper:
            return time(7, 0)
        elif "REEFER MIXTO 1" in dept_upper or "MIXTO 1" in dept_upper or "MIXTO1" in dept_upper:
            return time(13, 0)
        elif "REEFER DIURNO" in dept_upper or "DIURNO" in dept_upper:
            return time(7, 0)
        elif "REEFER MIXTO" in dept_upper or "MIXTO" in dept_upper:
            return time(15, 0)
        return time(7, 0)
    
    # Operaciones Bomba (Rotativo 6:00 o 18:00)
    if "BOMBA" in dept_upper:
        if entry_time and entry_time.hour >= 12:
            return time(18, 0)
        return time(6, 0)
    
    # Oficina Predio 2
    if predio == 2 and "OFICINA" in dept_upper:
        return time(7, 30)
    
    # Mixto (Supervisor / Despacho / Operaciones) -> 15:00
    if "MIXTO" in dept_upper or "15:00" in dept_upper:
        return time(15, 0)
    
    # Default Predio 1 (Oficina, Taller Chasis, Mantenimiento Limon, Operaciones Diurno, Despacho)
    if entry_time:
        if 5 <= entry_time.hour <= 11:
            return time(7, 0)
        elif 12 <= entry_time.hour <= 16:
            return time(15, 0)
        elif 17 <= entry_time.hour <= 21:
            return time(18, 0)

    return time(7, 0)

def evaluate_incidencia(entrada_raw, salida_raw, departamento="", predio=1, incidencia_actual=""):
    """
    Evaluates INCIDENCIA rule:
    - REVISAR: if entrada or salida is blank/empty/missing
    - TARDIA: if entrada minute >= 6 after expected start time
    - PRESENTE: if on time
    - Preserves special values like LIBRE, Incapacidad CCSS, Suspensión Sin if provided explicitly.
    """
    if incidencia_actual and str(incidencia_actual).strip().upper() in ["LIBRE", "INCAPACIDAD CCSS", "SUSPENSIÓN SIN", "SUSPENSION SIN"]:
        return str(incidencia_actual).strip()
    
    ent_clean = clean_time_str(entrada_raw)
    sal_clean = clean_time_str(salida_raw)
    
    # Blank / Missing rule -> REVISAR
    if not ent_clean or not sal_clean:
        return "REVISAR"
    
    t_ent = parse_time_obj(ent_clean)
    if not t_ent:
        return "REVISAR"
    
    t_exp = get_expected_start_time(departamento, predio, t_ent)
    
    exp_minutes = t_exp.hour * 60 + t_exp.minute
    ent_minutes = t_ent.hour * 60 + t_ent.minute
    
    diff = ent_minutes - exp_minutes
    
    # 6 minutes tolerance rule
    if diff >= 6:
        return "TARDIA"
    
    return "PRESENTE"
