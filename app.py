"""
Servidor Web Flask para el Módulo de Consulta y Evaluación Crediticia Bancaria.
Proporciona endpoints REST y renderiza la interfaz gráfica moderna tipo Banca/FinTech.
"""

import os
import io
import json
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import pandas as pd
from backend.credit_engine import CreditAnalysisEngine
from backend.sample_data import export_sample_files_to_disk
from backend.database import (
    init_db, get_all_clients, get_client_by_key, 
    save_client_to_db, generate_transactions_from_monthly_inputs
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, 'ejemplos_estados_cuenta')

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

engine = CreditAnalysisEngine()

# Inicializar Base de Datos SQLite y asegurar que existan los archivos de prueba en disco
init_db()
if not os.path.exists(SAMPLE_DIR) or len(os.listdir(SAMPLE_DIR)) == 0:
    export_sample_files_to_disk(SAMPLE_DIR)


@app.route('/')
def index():
    """Página principal del Dashboard Crediticio"""
    candidates = get_all_clients()
    sample_files = [f for f in os.listdir(SAMPLE_DIR) if f.endswith(('.csv', '.xlsx'))]
    return render_template('dashboard.html', candidates=candidates, sample_files=sample_files)


@app.route('/nuevo-cliente')
def nuevo_cliente_view():
    """Ventana independiente para registrar un nuevo cliente desde cero"""
    return render_template('nuevo_cliente.html')


@app.route('/api/candidates', methods=['GET'])
def list_candidates():
    """Lista los candidatos disponibles en la base de datos (precargados y personalizados)"""
    return jsonify(get_all_clients())


@app.route('/api/candidate/<candidate_key>', methods=['GET'])
def get_candidate_analysis(candidate_key):
    """Ejecuta el análisis de los últimos 6 meses para un candidato almacenado en SQLite"""
    try:
        client_info, txs = get_client_by_key(candidate_key)
        if not client_info or not txs:
            return jsonify({'success': False, 'error': f'Cliente {candidate_key} no encontrado en la base de datos.'}), 404

        analysis = engine.analyze_transactions(txs, client_info)
        return jsonify({'success': True, 'data': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/save-client', methods=['POST'])
def save_new_client():
    """
    Endpoint para crear y almacenar en la base de datos SQLite un cliente nuevo desde cero
    junto con sus movimientos de los últimos 6 meses.
    """
    try:
        data = request.json or {}
        client_info = data.get('client_info', {})
        monthly_data = data.get('monthly_data', [])
        raw_transactions = data.get('transactions', [])

        # Validaciones básicas
        if not client_info.get('nombre') or not client_info.get('rut_dni'):
            return jsonify({'success': False, 'error': 'El nombre completo y RUT/DNI son obligatorios.'}), 400

        # Si viene información mensual (6 meses), generar las transacciones
        if monthly_data and len(monthly_data) > 0:
            initial_balance = float(data.get('saldo_inicial', 1500.0))
            transactions = generate_transactions_from_monthly_inputs(monthly_data, initial_balance=initial_balance)
        elif raw_transactions and len(raw_transactions) > 0:
            transactions = raw_transactions
        else:
            return jsonify({'success': False, 'error': 'Debe ingresar al menos los movimientos de los últimos 6 meses.'}), 400

        # Guardar en base de datos SQLite
        perfil_key = save_client_to_db(client_info, transactions, es_personalizado=1)

        return jsonify({
            'success': True,
            'perfil_key': perfil_key,
            'message': f"Cliente {client_info['nombre']} guardado exitosamente en la base de datos.",
            'total_transacciones': len(transactions)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al guardar en base de datos: {str(e)}'}), 500



@app.route('/api/upload', methods=['POST'])
def upload_file():
    """
    Recibe un archivo CSV o Excel con transacciones,
    normaliza las columnas y genera el dictamen crediticio de 6 meses.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se envió ningún archivo.'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'success': False, 'error': 'Nombre de archivo vacío.'}), 400

    filename = file.filename.lower()
    try:
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            # Si el archivo tiene la hoja 'Movimientos', usarla; de lo contrario la primera
            excel_file = pd.ExcelFile(file)
            sheet_name = 'Movimientos' if 'Movimientos' in excel_file.sheet_names else excel_file.sheet_names[0]
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        else:
            return jsonify({'success': False, 'error': 'Formato no soportado. Debe ser CSV o Excel (.xlsx).'}), 400

        # Normalizar nombres de columnas a minúsculas y sin acentos
        col_map = {}
        for col in df.columns:
            clean_col = str(col).lower().strip()
            clean_col = clean_col.replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            
            if 'fecha' in clean_col or 'date' in clean_col:
                col_map[col] = 'fecha'
            elif 'monto' in clean_col or 'amount' in clean_col or 'importe' in clean_col or 'valor' in clean_col:
                col_map[col] = 'monto'
            elif 'tipo' in clean_col or 'type' in clean_col:
                col_map[col] = 'tipo'
            elif 'cat' in clean_col or 'rubro' in clean_col:
                col_map[col] = 'categoria'
            elif 'desc' in clean_col or 'concepto' in clean_col or 'detalle' in clean_col:
                col_map[col] = 'descripcion'
            elif 'saldo' in clean_col or 'balance' in clean_col:
                col_map[col] = 'saldo_resultante'
                
        df = df.rename(columns=col_map)
        
        # Validar campos indispensables
        required_cols = ['fecha', 'monto', 'tipo']
        missing = [rc for rc in required_cols if rc not in df.columns]
        if missing:
            return jsonify({
                'success': False, 
                'error': f'Faltan columnas requeridas en el archivo: {", ".join(missing)}. Las columnas deben incluir Fecha, Monto, Tipo (INGRESO/EGRESO).'
            }), 400

        # Rellenar columnas opcionales si faltan
        if 'categoria' not in df.columns:
            df['categoria'] = 'Varios'
        if 'descripcion' not in df.columns:
            df['descripcion'] = 'Movimiento registrado'
        if 'saldo_resultante' not in df.columns:
            # Reconstruir un saldo proyectado sumando ingresos y restando egresos
            saldo_simulado = 1000.0
            saldos = []
            for _, row in df.iterrows():
                m = float(row.get('monto', 0.0))
                t = str(row.get('tipo', '')).upper()
                if 'ING' in t:
                    saldo_simulado += m
                else:
                    saldo_simulado -= m
                saldos.append(round(saldo_simulado, 2))
            df['saldo_resultante'] = saldos

        transactions = df.to_dict(orient='records')
        
        # Extraer nombre del cliente del formulario si fue provisto
        client_name = request.form.get('nombre_cliente', os.path.splitext(file.filename)[0].replace('_', ' ').title())
        client_dni = request.form.get('rut_dni', 'Importado por Archivo')
        client_ocupacion = request.form.get('ocupacion', 'Titular de Cuenta')

        client_info = {
            'id': 'IMP-' + str(abs(hash(file.filename)) % 10000),
            'nombre': client_name,
            'rut_dni': client_dni,
            'ocupacion': client_ocupacion,
            'empresa': 'Registrada en Estado de Cuenta',
            'tipo_contrato': 'Auditado por Movimientos',
            'antiguedad_laboral_anios': 'N/D',
            'antiguedad_bancaria_meses': 6,
            'avatar': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Candidato Evaluado vía Archivo Externo'
        }

        analysis = engine.analyze_transactions(transactions, client_info)
        return jsonify({'success': True, 'data': analysis})

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al procesar el archivo: {str(e)}'}), 500


@app.route('/api/simulate-loan', methods=['POST'])
def simulate_loan():
    """
    Simula dinámicamente un crédito bancario con monto y plazo personalizados,
    validando si la cuota supera la capacidad de pago máxima mensual del candidato.
    """
    try:
        data = request.json or {}
        monto = float(data.get('monto', 5000.0))
        plazo_meses = int(data.get('plazo_meses', 24))
        tasa_anual_pct = float(data.get('tasa_anual_pct', 18.0))
        capacidad_maxima = float(data.get('capacidad_maxima', 500.0))
        
        if monto <= 0 or plazo_meses <= 0:
            return jsonify({'success': False, 'error': 'Monto y plazo deben ser mayores a cero.'}), 400

        tasa_mensual = (1 + (tasa_anual_pct / 100.0)) ** (1.0 / 12.0) - 1.0
        cuota_mensual = round(monto * (tasa_mensual / (1.0 - (1.0 + tasa_mensual) ** (-plazo_meses))), 2)
        total_a_pagar = round(cuota_mensual * plazo_meses, 2)
        intereses_totales = round(total_a_pagar - monto, 2)
        
        excede_capacidad = cuota_mensual > capacidad_maxima
        porcentaje_compromiso = round((cuota_mensual / capacidad_maxima * 100), 1) if capacidad_maxima > 0 else 999.0
        
        return jsonify({
            'success': True,
            'monto_solicitado': monto,
            'plazo_meses': plazo_meses,
            'tasa_anual_pct': tasa_anual_pct,
            'tasa_mensual_pct': round(tasa_mensual * 100, 2),
            'cuota_mensual': cuota_mensual,
            'total_a_pagar': total_a_pagar,
            'intereses_totales': intereses_totales,
            'capacidad_maxima': capacidad_maxima,
            'excede_capacidad': excede_capacidad,
            'porcentaje_compromiso': porcentaje_compromiso,
            'estado': 'ALERTA_CAPACIDAD' if excede_capacidad else 'APROBADO_VIABLE'
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/download-template')
def download_template():
    """Descarga una plantilla modelo Excel para que el usuario pueda ingresar sus propios datos"""
    template_data = [
        {'fecha': '2026-05-15', 'descripcion': 'ABONO REMUNERACION MENSUAL', 'categoria': 'Nomina/Sueldo', 'tipo': 'INGRESO', 'monto': 2500.0, 'saldo_resultante': 3200.0},
        {'fecha': '2026-05-18', 'descripcion': 'PAGO ARRIENDO PROPIEDAD', 'categoria': 'Servicios/Vivienda', 'tipo': 'EGRESO', 'monto': 700.0, 'saldo_resultante': 2500.0},
        {'fecha': '2026-05-20', 'descripcion': 'SUPERMERCADO Y ALIMENTOS', 'categoria': 'Alimentacion/Supermercado', 'tipo': 'EGRESO', 'monto': 200.0, 'saldo_resultante': 2300.0},
        {'fecha': '2026-05-25', 'descripcion': 'PAGO CUOTA PRESTAMO VIGENTE', 'categoria': 'Cuota Prestamo', 'tipo': 'EGRESO', 'monto': 180.0, 'saldo_resultante': 2120.0},
        {'fecha': '2026-06-15', 'descripcion': 'ABONO REMUNERACION MENSUAL', 'categoria': 'Nomina/Sueldo', 'tipo': 'INGRESO', 'monto': 2500.0, 'saldo_resultante': 4620.0}
    ]
    df = pd.DataFrame(template_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Movimientos', index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='plantilla_movimientos_6_meses.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@app.route('/api/download-sample/<filename>')
def download_sample_file(filename):
    """Permite descargar cualquiera de los archivos CSV/Excel de prueba generados"""
    return send_from_directory(SAMPLE_DIR, filename, as_attachment=True)


if __name__ == '__main__':
    print("=" * 70)
    print("  CREDITSENSE - MODULO DE EVALUACION CREDITICIA BANCARIA (6 MESES)")
    print("  Iniciando servidor local en http://127.0.0.1:5000 ...")
    print("=" * 70)
    app.run(host='127.0.0.1', port=5000, debug=True)
