"""
Generador de Perfiles y Movimientos Bancarios de Prueba (Últimos 6 meses).
Genera datos sintéticos con comportamientos financieros diversos para pruebas del motor de crédito.
"""

import os
from datetime import datetime, timedelta
import random
import pandas as pd


def generate_candidate_transactions(candidate_type: str) -> tuple[dict, list[dict]]:
    """
    Genera el perfil del cliente y sus transacciones bancarias detalladas para los últimos 6 meses.
    candidate_type: 'carlos_excelente', 'lucia_estable', 'rodrigo_variable', 'mariana_endeudada', 'jorge_sobregirado'
    """
    # Fechas de simulación: Mayo 2026 a Octubre 2026 (6 meses completos)
    start_date = datetime(2026, 5, 1)
    end_date = datetime(2026, 10, 31)
    
    transactions = []
    
    if candidate_type == 'carlos_excelente':
        client_info = {
            'id': 'CLI-1001',
            'nombre': 'Carlos Mendoza Silva',
            'rut_dni': '15.892.411-K',
            'ocupacion': 'Ingeniero de Software Senior / Tech Lead',
            'empresa': 'Global Tech Solutions S.A.',
            'tipo_contrato': 'Indefinido',
            'antiguedad_laboral_anios': 4.5,
            'antiguedad_bancaria_meses': 48,
            'avatar': 'https://images.unsplash.com/photo-1534528741775-53994a69daeb?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Candidato Premium (Aprobado A+)'
        }
        
        balance = 5200.0
        # Ingreso mensual fijo de nómina de $4,600 los días 28-30
        curr_date = start_date
        while curr_date <= end_date:
            day = curr_date.day
            
            # Nómina mensual
            if day == 28:
                monto = 4600.0 + random.uniform(-50, 80)
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'ABONO NOMINA / GLOBAL TECH SOLUTIONS',
                    'categoria': 'Nomina/Sueldo',
                    'tipo': 'INGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
            
            # Dividendo o inversión esporádica en julio
            if curr_date.month == 7 and day == 15:
                monto = 1200.0
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'DIVIDENDOS FONDOS MUTUOS INVERSION',
                    'categoria': 'Inversiones',
                    'tipo': 'INGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Gastos fijos (Arriendo/Vivienda) día 5
            if day == 5:
                monto = 1100.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TRANSF. ARRIENDO DEPTO 804',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Servicios básicos día 8
            if day == 8:
                monto = 190.0 + random.uniform(-20, 30)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'PAGO AUTOMATICO AGUA, LUZ, FIBRA 600M',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Cuota de crédito hipotecario o auto día 12 (DTI bajo: $320)
            if day == 12:
                monto = 320.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'CUOTA PRESTAMO VEHICULAR 18/36',
                    'categoria': 'Cuota Prestamo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Supermercado 3 veces al mes
            if day in [6, 17, 26]:
                monto = 180.0 + random.uniform(-30, 40)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'COMPRA SUPERMERCADO JUMBO/LIDER',
                    'categoria': 'Alimentacion/Supermercado',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Ocio y restaurantes fines de semana
            if curr_date.weekday() in [5, 6] and random.random() < 0.35:
                monto = 65.0 + random.uniform(-15, 60)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'RESTAURANTE / DELIVERY UBER EATS',
                    'categoria': 'Ocio/Restaurantes',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            curr_date += timedelta(days=1)

    elif candidate_type == 'lucia_estable':
        client_info = {
            'id': 'CLI-1002',
            'nombre': 'Lucía Fernández Rios',
            'rut_dni': '17.204.933-4',
            'ocupacion': 'Analista Contable y Finanzas',
            'empresa': 'Servicios Contables del Sur Ltda.',
            'tipo_contrato': 'Indefinido',
            'antiguedad_laboral_anios': 3.0,
            'antiguedad_bancaria_meses': 32,
            'avatar': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Candidato Aprobado Estándar'
        }
        
        balance = 1650.0
        curr_date = start_date
        while curr_date <= end_date:
            day = curr_date.day
            
            # Sueldo fijo de $2,100
            if day == 30 or (curr_date.month == 2 and day == 28):
                monto = 2100.0
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TRANSFERENCIA SUELDO SERVICIOS CONTABLES',
                    'categoria': 'Nomina/Sueldo',
                    'tipo': 'INGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Vivienda / Gastos comunes
            if day == 4:
                monto = 550.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'PAGO ARRIENDO Y GASTO COMUN',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Préstamo estudiantil / personal ($230 mensual)
            if day == 10:
                monto = 230.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'CARGO CUOTA CREDITO ESTUDIOS',
                    'categoria': 'Cuota Prestamo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Servicios día 14
            if day == 14:
                monto = 110.0 + random.uniform(-10, 15)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'PAGO SERVICIOS ELECTRICIDAD Y TELEFONIA',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Supermercado
            if day in [7, 21]:
                monto = 160.0 + random.uniform(-20, 30)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'SUPERMERCADOS Y TIENDAS DE ABARROTES',
                    'categoria': 'Alimentacion/Supermercado',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Ocio
            if curr_date.weekday() == 5 and random.random() < 0.4:
                monto = 45.0 + random.uniform(-10, 20)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'CAFETERIA / CINE / SALIDAS',
                    'categoria': 'Ocio/Restaurantes',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            curr_date += timedelta(days=1)

    elif candidate_type == 'rodrigo_variable':
        client_info = {
            'id': 'CLI-1003',
            'nombre': 'Rodrigo Morales Peña',
            'rut_dni': '16.551.820-2',
            'ocupacion': 'Diseñador UI/UX Independiente (Freelance)',
            'empresa': 'Honorarios / Múltiples Clientes',
            'tipo_contrato': 'Prestador de Servicios',
            'antiguedad_laboral_anios': 2.0,
            'antiguedad_bancaria_meses': 24,
            'avatar': 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Candidato Condicionado (Riesgo Medio)'
        }
        
        balance = 1400.0
        curr_date = start_date
        while curr_date <= end_date:
            day = curr_date.day
            
            # Ingresos variables por proyectos (adelanto día 4 y cierre día 18)
            if day == 4:
                monto = random.choice([800.0, 950.0, 1100.0])
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': f'ANTICIPO FACTURA PROYECTO #{random.randint(10, 99)}',
                    'categoria': 'Transferencia Recibida',
                    'tipo': 'INGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
            elif day == 18:
                monto = random.choice([700.0, 900.0, 1200.0, 1500.0])
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': f'LIQUIDACION PROYECTO CLIENTE #{random.randint(10, 99)}',
                    'categoria': 'Transferencia Recibida',
                    'tipo': 'INGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Vivienda y coworking
            if day == 5:
                monto = 680.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TRANSFERENCIA ARRIENDO DEPARTAMENTO',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Cuota de crédito comercial/notebook ($150)
            if day == 18:
                monto = 150.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'CUOTA PRESTAMO EQUIPO 06/18',
                    'categoria': 'Cuota Prestamo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Herramientas software
            if day == 14:
                monto = 240.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'SUSCRIPCIONES FIGMA, ADOBE, HOSTING, CHATGPT PLUS',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Supermercado y alimentación
            if day in [8, 22]:
                monto = 230.0 + random.uniform(-10, 20)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'COMPRA SUPERMERCADO Y VIVERES',
                    'categoria': 'Alimentacion/Supermercado',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Ocio y reuniones
            if curr_date.weekday() in [5, 6] and random.random() < 0.5:
                monto = 90.0 + random.uniform(-10, 20)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'SALIDAS RESTAURANTE / REUNIONES CLIENTES',
                    'categoria': 'Ocio/Restaurantes',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            curr_date += timedelta(days=1)

    elif candidate_type == 'mariana_endeudada':
        client_info = {
            'id': 'CLI-1004',
            'nombre': 'Mariana Ortiz Valenzuela',
            'rut_dni': '18.312.905-1',
            'ocupacion': 'Ejecutiva Comercial',
            'empresa': 'Distribuidora Retail Andina',
            'tipo_contrato': 'Indefinido',
            'antiguedad_laboral_anios': 1.5,
            'antiguedad_bancaria_meses': 18,
            'avatar': 'https://images.unsplash.com/photo-1544005313-94ddf0286df2?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Candidato Rechazado (Sobreendeudamiento)'
        }
        
        balance = 800.0
        curr_date = start_date
        while curr_date <= end_date:
            day = curr_date.day
            
            # Ingreso de nómina $2,300
            if day == 30 or (curr_date.month == 2 and day == 28):
                monto = 2300.0
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'ABONO NOMINA DISTRIBUIDORA RETAIL',
                    'categoria': 'Nomina/Sueldo',
                    'tipo': 'INGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # ALTO ENDEUDAMIENTO: Paga 3 créditos distintos al mes ($1,150 en total de deuda, > 50% de su sueldo!)
            if day == 3:
                monto = 480.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'PAGO MINIMO TARJETA RETAIL FALABELLA',
                    'categoria': 'Cuota Prestamo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
            if day == 7:
                monto = 380.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'CUOTA PRESTAMO DE CONSUMO BANCO BICE 12/24',
                    'categoria': 'Cuota Prestamo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
            if day == 15:
                monto = 290.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'PAGO CUOTA CREDITO AUTOMOTRIZ',
                    'categoria': 'Cuota Prestamo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Arriendo
            if day == 5:
                monto = 600.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TRANSFERENCIA ARRIENDO DEPARTAMENTO',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Gastos cotidianos que exceden su presupuesto
            if day in [11, 25]:
                monto = 175.0 + random.uniform(-10, 20)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'SUPERMERCADO Y FARMACIA',
                    'categoria': 'Alimentacion/Supermercado',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Compras con tarjeta y ropa
            if day in [18, 28] and random.random() < 0.6:
                monto = 120.0 + random.uniform(-10, 30)
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TIENDAS POR DEPARTAMENTO / ZARA / H&M',
                    'categoria': 'Compras Tarjeta',
                    'tipo': 'EGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            curr_date += timedelta(days=1)

    else:  # jorge_sobregirado
        client_info = {
            'id': 'CLI-1005',
            'nombre': 'Jorge Benítez Cárcamo',
            'rut_dni': '14.981.602-5',
            'ocupacion': 'Asesor Independiente',
            'empresa': 'Servicios Varios',
            'tipo_contrato': 'Honorarios',
            'antiguedad_laboral_anios': 1.0,
            'antiguedad_bancaria_meses': 12,
            'avatar': 'https://images.unsplash.com/photo-1500648767791-00dcc994a43e?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Candidato Rechazado (Sobregiros e Insolvencia)'
        }
        
        balance = 250.0
        curr_date = start_date
        while curr_date <= end_date:
            day = curr_date.day
            
            # Ingresos irregulares y decrecientes
            if day == 12:
                # Empieza en $1,800 y va cayendo a $1,000 en los últimos meses
                mes_idx = (curr_date.year - 2026) * 12 + curr_date.month - 5
                monto = max(900.0, 1800.0 - (mes_idx * 160.0))
                balance += monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TRANSFERENCIA DEPOSITOS HONORARIOS',
                    'categoria': 'Transferencia Recibida',
                    'tipo': 'INGRESO',
                    'monto': round(monto, 2),
                    'saldo_resultante': round(balance, 2)
                })
                
            # Arriendo fijo de $550
            if day == 6:
                monto = 550.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'TRANSFERENCIA ARRIENDO',
                    'categoria': 'Servicios/Vivienda',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Retiros constantes de efectivo en cajeros
            if day in [9, 19, 27]:
                monto = 150.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'GIRO CAJERO AUTOMATICO REDBANC',
                    'categoria': 'Retiro Efectivo',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Gastos en apuestas / juegos o débitos
            if day in [14, 24] and random.random() < 0.5:
                monto = 110.0
                balance -= monto
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'CARGO CASINO ONLINE / PLATAFORMA APUESTAS',
                    'categoria': 'Ocio/Restaurantes',
                    'tipo': 'EGRESO',
                    'monto': monto,
                    'saldo_resultante': round(balance, 2)
                })
                
            # Eventos explícitos de SOBREGIRO en julio y septiembre
            if (curr_date.month == 7 and day == 26) or (curr_date.month == 9 and day == 28):
                if balance > 0:
                    balance = -180.0
                else:
                    balance -= 120.0
                transactions.append({
                    'fecha': curr_date.strftime('%Y-%m-%d'),
                    'descripcion': 'COMISION POR SOBREGIRO / SALDO NEGATIVO LINEA CREDITO',
                    'categoria': 'Sobregiro/Comision',
                    'tipo': 'EGRESO',
                    'monto': 45.0,
                    'saldo_resultante': round(balance, 2)
                })
                
            curr_date += timedelta(days=1)

    return client_info, transactions


def export_sample_files_to_disk(output_dir: str):
    """
    Genera y guarda en disco los archivos CSV y Excel de ejemplo para que el usuario pueda probar
    la función de subida de archivos (Upload).
    """
    os.makedirs(output_dir, exist_ok=True)
    
    candidates = ['carlos_excelente', 'lucia_estable', 'rodrigo_variable', 'mariana_endeudada', 'jorge_sobregirado']
    
    for c in candidates:
        client, txs = generate_candidate_transactions(c)
        df = pd.DataFrame(txs)
        
        # Guardar en CSV
        csv_filename = os.path.join(output_dir, f"{client['id']}_{c}_6_meses.csv")
        df.to_csv(csv_filename, index=False, encoding='utf-8')
        
        # Guardar en Excel
        xlsx_filename = os.path.join(output_dir, f"{client['id']}_{c}_6_meses.xlsx")
        with pd.ExcelWriter(xlsx_filename, engine='openpyxl') as writer:
            df.to_excel(writer, sheet_name='Movimientos', index=False)
            
            # Hoja informativa del cliente
            df_info = pd.DataFrame([client])
            df_info.to_excel(writer, sheet_name='Datos_Cliente', index=False)
            
    print(f"Archivos de prueba exportados exitosamente en: {output_dir}")


def get_all_demo_candidates():
    """Devuelve la lista con los 5 perfiles para carga rápida en la interfaz."""
    candidates = ['carlos_excelente', 'lucia_estable', 'rodrigo_variable', 'mariana_endeudada', 'jorge_sobregirado']
    result = []
    for c in candidates:
        client, txs = generate_candidate_transactions(c)
        result.append({
            'perfil_key': c,
            'client_info': client,
            'total_transacciones': len(txs)
        })
    return result
