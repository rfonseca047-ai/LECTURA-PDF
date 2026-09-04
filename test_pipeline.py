import os
from datetime import datetime
from rules_engine import evaluate_incidencia, clean_time_str
from excel_generator import create_excel_report

def run_sample_test():
    sample_data = [
        {"codigo": "702950206", "nombre": "FENNELL ARAYA BRITTANY", "departamento": "OFICINA", "entrada": "6:52", "salida": ""},
        {"codigo": "702790952", "nombre": "ANCHIA BONILLA ALEXANDER", "departamento": "OPERACIONES BOMBA", "entrada": "06:05", "salida": "18:00"},
        {"codigo": "111460931", "nombre": "MURRAY DIXON CINDY ELENA", "departamento": "OPERACIONES BOMBA", "entrada": "17:55", "salida": "06:00"},
        {"codigo": "702090180", "nombre": "SOBALBARRO FARQUEHARSON ISAAC", "departamento": "OPERACIONES BOMBA", "entrada": "6:55", "salida": "17:05"},
        {"codigo": "302540824", "nombre": "ARCE VILLEGAS JOSE", "departamento": "TALLER CHASIS", "entrada": "7:53", "salida": "17:14"},
        {"codigo": "132000139611", "nombre": "CORZO AJBAL LEONEL", "departamento": "TALLER CHASIS", "entrada": "7:53", "salida": "17:14"},
        {"codigo": "132000401936", "nombre": "CORZO COLOCHO ERICK", "departamento": "TALLER CHASIS", "entrada": "7:53", "salida": "17:14"},
        {"codigo": "326373772", "nombre": "CORZO COLOCHO KELVIN", "departamento": "TALLER CHASIS", "entrada": "7:55", "salida": "17:03"},
        {"codigo": "700730293", "nombre": "GRANT LOAICIGA ABEL", "departamento": "TALLER CHASIS", "entrada": "", "salida": ""},
        {"codigo": "155853895823", "nombre": "LAZO CASTILLO JOSE", "departamento": "TALLER CHASIS", "entrada": "05:52", "salida": "17:00"},
        {"codigo": "502300625", "nombre": "RIVAS LOBO JESUS", "departamento": "TALLER CHASIS", "entrada": "6:36", "salida": "17:00"},
        {"codigo": "702440250", "nombre": "SOLIS VANEGAS JEAN CARLOS", "departamento": "TALLER CHASIS", "entrada": "6:36", "salida": "17:00"},
        {"codigo": "701100267", "nombre": "ZAPATA ANGULO GERARDO", "departamento": "TALLER CHASIS", "entrada": "6:45", "salida": "17:02"},
        {"codigo": "701230353", "nombre": "BALTODANO SAMUDIO SERGIO", "departamento": "MANTENIMIENTO LIMON", "entrada": "06:55", "salida": "17:00"},
        {"codigo": "701260787", "nombre": "BARRANTES CORRALES LIZETH", "departamento": "MANTENIMIENTO LIMON", "entrada": "05:57", "salida": "12:06"}
    ]

    processed = []
    print("=== TEST RUN RESULTS ===")
    for row in sample_data:
        ent = clean_time_str(row["entrada"])
        sal = clean_time_str(row["salida"])
        inc = evaluate_incidencia(ent, sal, departamento=row["departamento"], predio=1)
        row["entrada"] = ent
        row["salida"] = sal
        row["incidencia"] = inc
        row["predio"] = 1
        processed.append(row)
        print(f"#{row['codigo']} | {row['nombre'][:20]:<20} | Ent: {ent or 'VACIO':<6} | Sal: {sal or 'VACIO':<6} | INC: {inc}")

    date_test = datetime(2026, 8, 27) # 27-Aug-26 Thursday
    wb = create_excel_report(processed, date_val=date_test, predio_val=1)
    output_path = "Prueba_Planilla_Generada.xlsx"
    wb.save(output_path)
    print(f"\nExcel generado con éxito en: {os.path.abspath(output_path)}")

if __name__ == "__main__":
    run_sample_test()
