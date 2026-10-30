"""
Servidor Web Flask para CreditSense - Plataforma de Evaluación Crediticia Multi-Banco.
Controla los módulos de Clientes, Carga de Movimientos Multi-Banco y Simulador Crediticio.
"""

import os
import io
import json
import uuid
import base64
from flask import Flask, render_template, request, jsonify, send_file, send_from_directory
import pandas as pd
from backend.credit_engine import CreditAnalysisEngine
from backend.sample_data import export_sample_files_to_disk
from backend.database import (
    init_db, get_all_clients, get_client_by_key, get_client_by_id, get_client_full_data,
    extract_monthly_summary_from_transactions,
    save_client_to_db, update_client_info, delete_client_by_id,
    append_transactions_to_client, generate_transactions_from_monthly_inputs,
    rename_bank_for_client, delete_bank_movements, get_client_banks_and_files
)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SAMPLE_DIR = os.path.join(BASE_DIR, 'ejemplos_estados_cuenta')
UPLOAD_AVATAR_DIR = os.path.join(BASE_DIR, 'static', 'uploads', 'avatars')
os.makedirs(UPLOAD_AVATAR_DIR, exist_ok=True)

app = Flask(__name__, template_folder=os.path.join(BASE_DIR, 'templates'), static_folder=os.path.join(BASE_DIR, 'static'))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB max

engine = CreditAnalysisEngine()

# Inicializar Base de Datos SQLite y asegurar que existan los archivos de prueba en disco
init_db()
if not os.path.exists(SAMPLE_DIR) or len(os.listdir(SAMPLE_DIR)) == 0:
    export_sample_files_to_disk(SAMPLE_DIR)


# =========================================================================
# VISTAS PRINCIPALES (FRONTEND)
# =========================================================================

@app.route('/')
def home_portal():
    """Portal Principal de Bienvenida y Acceso a los 3 Módulos"""
    candidates = get_all_clients()
    return render_template('index.html', candidates=candidates)


@app.route('/clientes')
def clientes_view():
    """Módulo 1: Gestión de Cartera de Clientes (Consulta, Edición, Eliminación)"""
    candidates = get_all_clients()
    return render_template('clientes.html', candidates=candidates)


@app.route('/carga-movimientos')
def carga_movimientos_view():
    """Módulo 2: Carga y Consolidación de Movimientos de Diferentes Bancos"""
    candidates = get_all_clients()
    return render_template('carga_movimientos.html', candidates=candidates)


@app.route('/simulador')
def simulador_view():
    """Módulo 3: Simulador y Desglose Analítico de Scoring y Dictamen"""
    candidates = get_all_clients()
    sample_files = [f for f in os.listdir(SAMPLE_DIR) if f.endswith(('.csv', '.xlsx'))]
    return render_template('dashboard.html', candidates=candidates, sample_files=sample_files)


@app.route('/nuevo-cliente')
def nuevo_cliente_view():
    """Ventana independiente para registrar o editar un cliente completo con sus movimientos y foto"""
    candidates = get_all_clients()
    selected_id = request.args.get('client_id', '').strip()
    return render_template('nuevo_cliente.html', candidates=candidates, selected_client_id=selected_id)


# =========================================================================
# API REST (CLIENTES Y CONSULTAS)
# =========================================================================

@app.route('/api/upload-avatar', methods=['POST'])
def upload_avatar():
    """Recibe una imagen (archivo multipart o Data URI base64) y la almacena en static/uploads/avatars/."""
    try:
        # 1. Caso archivo subido vía multipart/form-data
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                ext = os.path.splitext(file.filename)[1].lower()
                if ext not in ['.jpg', '.jpeg', '.png', '.webp', '.svg']:
                    ext = '.jpg'
                filename = f"avatar_{uuid.uuid4().hex[:12]}{ext}"
                filepath = os.path.join(UPLOAD_AVATAR_DIR, filename)
                file.save(filepath)
                return jsonify({'success': True, 'avatar_url': f"/static/uploads/avatars/{filename}"})

        # 2. Caso Data URI Base64 enviado en JSON
        data = request.json or {}
        image_data = data.get('image_data', '')
        if image_data and 'base64,' in image_data:
            header, encoded = image_data.split('base64,', 1)
            ext = '.png' if 'png' in header else ('.webp' if 'webp' in header else ('.svg' if 'svg' in header else '.jpg'))
            filename = f"avatar_{uuid.uuid4().hex[:12]}{ext}"
            filepath = os.path.join(UPLOAD_AVATAR_DIR, filename)
            with open(filepath, 'wb') as fh:
                fh.write(base64.b64decode(encoded))
            return jsonify({'success': True, 'avatar_url': f"/static/uploads/avatars/{filename}"})

        return jsonify({'success': False, 'error': 'No se recibió ninguna imagen válida.'}), 400

    except Exception as e:
        return jsonify({'success': False, 'error': f"Error al guardar imagen: {str(e)}"}), 500


@app.route('/api/client/<client_id>', methods=['GET'])
def get_client_profile_api(client_id):
    """Obtiene el perfil completo de un cliente y el resumen de sus movimientos mensuales."""
    try:
        client_info, txs = get_client_full_data(client_id)
        if not client_info:
            return jsonify({'success': False, 'error': f'Cliente {client_id} no encontrado.'}), 404

        monthly_summary = extract_monthly_summary_from_transactions(txs)
        return jsonify({
            'success': True,
            'client': client_info,
            'monthly_summary': monthly_summary,
            'total_transacciones': len(txs)
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400

@app.route('/api/candidates', methods=['GET'])
def list_candidates():
    """Lista todos los clientes disponibles en la base de datos SQLite"""
    return jsonify(get_all_clients())


@app.route('/api/candidate/<candidate_key>', methods=['GET'])
def get_candidate_analysis(candidate_key):
    """Ejecuta el análisis de 6 meses para un candidato almacenado en SQLite"""
    try:
        client_info, txs = get_client_by_key(candidate_key)
        if not client_info or not txs:
            return jsonify({'success': False, 'error': f'Cliente {candidate_key} no encontrado en la base de datos.'}), 404

        analysis = engine.analyze_transactions(txs, client_info)
        return jsonify({'success': True, 'data': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/client/update', methods=['POST'])
def update_client():
    """Modifica la información personal y laboral de un cliente existente"""
    try:
        data = request.json or {}
        client_id = data.get('client_id')
        updated_info = data.get('updated_info', {})

        if not client_id or not updated_info:
            return jsonify({'success': False, 'error': 'Faltan parámetros requeridos.'}), 400

        success = update_client_info(client_id, updated_info)
        if success:
            return jsonify({'success': True, 'message': 'Cliente actualizado correctamente.'})
        return jsonify({'success': False, 'error': 'No se encontró el cliente para actualizar.'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/client/delete', methods=['POST'])
def delete_client():
    """Elimina permanentemente un cliente y sus transacciones de la base de datos"""
    try:
        data = request.json or {}
        client_id = data.get('client_id')

        if not client_id:
            return jsonify({'success': False, 'error': 'ID de cliente no proporcionado.'}), 400

        success = delete_client_by_id(client_id)
        if success:
            return jsonify({'success': True, 'message': 'Cliente eliminado exitosamente.'})
        return jsonify({'success': False, 'error': 'No se encontró el cliente a eliminar.'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/save-client', methods=['POST'])
def save_new_client():
    """Crea y almacena en SQLite un cliente nuevo desde cero con sus movimientos"""
    try:
        data = request.json or {}
        client_info = data.get('client_info', {})
        monthly_data = data.get('monthly_data', [])
        raw_transactions = data.get('transactions', [])

        if not client_info.get('nombre') or not client_info.get('rut_dni'):
            return jsonify({'success': False, 'error': 'El nombre y RUT/DNI son obligatorios.'}), 400

        if monthly_data and len(monthly_data) > 0:
            initial_balance = float(data.get('saldo_inicial', 1500.0))
            transactions = generate_transactions_from_monthly_inputs(monthly_data, initial_balance=initial_balance)
        elif raw_transactions and len(raw_transactions) > 0:
            transactions = raw_transactions
        else:
            return jsonify({'success': False, 'error': 'Debe ingresar al menos los movimientos de los últimos 6 meses.'}), 400

        perfil_key = save_client_to_db(client_info, transactions, es_personalizado=1)

        return jsonify({
            'success': True,
            'perfil_key': perfil_key,
            'message': f"Cliente {client_info['nombre']} guardado exitosamente en SQLite.",
            'total_transacciones': len(transactions)
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al guardar en base de datos: {str(e)}'}), 500


# =========================================================================
# API REST (CARGA MULTI-BANCO Y SIMULACIÓN)
# =========================================================================

@app.route('/api/upload-bank-movements', methods=['POST'])
def upload_bank_movements():
    """
    Recibe un archivo CSV o Excel para un cliente específico y permite
    acumular los movimientos provenientes de diferentes bancos.
    """
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se envió ningún archivo.'}), 400
        
    file = request.files['file']
    client_id = request.form.get('client_id')
    banco_origen = request.form.get('banco_origen', 'Banco Adicional').strip() or 'Banco Adicional'
    acumular = request.form.get('acumular', 'true').lower() == 'true'

    if not client_id:
        return jsonify({'success': False, 'error': 'Debe seleccionar un cliente.'}), 400

    client_record = get_client_by_id(client_id)
    if not client_record:
        return jsonify({'success': False, 'error': 'Cliente no encontrado en la base de datos.'}), 404

    try:
        filename = file.filename.lower()
        if filename.endswith('.csv'):
            df = pd.read_csv(file)
        elif filename.endswith(('.xlsx', '.xls')):
            excel_file = pd.ExcelFile(file)
            sheet_name = 'Movimientos' if 'Movimientos' in excel_file.sheet_names else excel_file.sheet_names[0]
            df = pd.read_excel(excel_file, sheet_name=sheet_name)
        else:
            return jsonify({'success': False, 'error': 'Formato no admitido. Debe ser CSV o Excel (.xlsx).'}), 400

        # Normalizar columnas
        col_map = {}
        for col in df.columns:
            clean_col = str(col).lower().strip().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            if 'fecha' in clean_col or 'date' in clean_col:
                col_map[col] = 'fecha'
            elif 'monto' in clean_col or 'amount' in clean_col or 'importe' in clean_col:
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

        if 'fecha' not in df.columns or 'monto' not in df.columns or 'tipo' not in df.columns:
            return jsonify({'success': False, 'error': 'El archivo debe contener al menos las columnas Fecha, Monto y Tipo (INGRESO/EGRESO).'}), 400

        if 'categoria' not in df.columns: df['categoria'] = 'Varios'
        if 'descripcion' not in df.columns: df['descripcion'] = f'Movimiento {banco_origen}'
        if 'saldo_resultante' not in df.columns: df['saldo_resultante'] = 0.0

        new_transactions = df.to_dict(orient='records')

        # Acumular o reemplazar en SQLite con archivo_origen registrado
        agregadas = append_transactions_to_client(
            client_id=client_id,
            new_transactions=new_transactions,
            banco_origen=banco_origen,
            archivo_origen=file.filename,
            reemplazar=(not acumular)
        )

        # Calcular totales acumulados
        client_info, all_txs = get_client_by_key(client_record['perfil_key'])
        df_all = pd.DataFrame(all_txs)
        total_ingresos = float(df_all[df_all['tipo'].str.contains('ING', case=False, na=False)]['monto'].sum()) if not df_all.empty else 0.0
        total_egresos = float(df_all[df_all['tipo'].str.contains('EGR', case=False, na=False)]['monto'].sum()) if not df_all.empty else 0.0

        return jsonify({
            'success': True,
            'message': f"Se han {'acumulado' if acumular else 'reemplazado'} {agregadas} movimientos de {banco_origen} ({file.filename}) para {client_record['nombre']}.",
            'transacciones_agregadas': agregadas,
            'total_transacciones_cliente': len(all_txs),
            'total_ingresos_acumulados': round(total_ingresos, 2),
            'total_egresos_acumulados': round(total_egresos, 2),
            'bancos_consolidados': client_info['bancos'],
            'perfil_key': client_record['perfil_key']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': f'Error al procesar movimientos: {str(e)}'}), 500


@app.route('/api/client/<client_id>/banks', methods=['GET'])
def get_client_banks_api(client_id):
    """Devuelve la lista de entidades bancarias y archivos vinculados para un cliente"""
    try:
        banks_list = get_client_banks_and_files(client_id)
        return jsonify({'success': True, 'banks': banks_list})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/client/rename-bank', methods=['POST'])
def rename_bank_api():
    """Modifica el nombre de una entidad bancaria vinculada a un cliente"""
    try:
        data = request.json or {}
        client_id = data.get('client_id')
        old_bank_name = data.get('old_bank_name', '').strip()
        new_bank_name = data.get('new_bank_name', '').strip()

        if not client_id or not old_bank_name or not new_bank_name:
            return jsonify({'success': False, 'error': 'Parámetros insuficientes.'}), 400

        success = rename_bank_for_client(client_id, old_bank_name, new_bank_name)
        if success:
            return jsonify({'success': True, 'message': f"Banco renombrado de '{old_bank_name}' a '{new_bank_name}' exitosamente."})
        return jsonify({'success': False, 'error': 'No se encontraron movimientos asociados a ese banco para renombrar.'}), 404

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/client/delete-bank-movements', methods=['POST'])
def delete_bank_movements_api():
    """
    Elimina los movimientos de un banco o archivo específico para un cliente
    y realiza el re-cálculo financiero inmediato de ingresos, débitos y scoring.
    """
    try:
        data = request.json or {}
        client_id = data.get('client_id')
        banco_origen = data.get('banco_origen', '').strip()
        archivo_origen = data.get('archivo_origen', '').strip() or None

        if not client_id or not banco_origen:
            return jsonify({'success': False, 'error': 'ID de cliente y nombre de banco son requeridos.'}), 400

        client_record = get_client_by_id(client_id)
        if not client_record:
            return jsonify({'success': False, 'error': 'Cliente no encontrado.'}), 404

        # Eliminar movimientos y recalcular saldos continuos
        result = delete_bank_movements(client_id, banco_origen, archivo_origen)

        # Re-evaluar scoring y clasificación con los movimientos restantes
        client_info, remaining_txs = get_client_by_key(client_record['perfil_key'])
        
        nuevo_score = 0
        nueva_decision = "SIN_DATOS"
        nuevo_riesgo = "Sin movimientos registrados"

        if remaining_txs:
            analysis = engine.analyze_transactions(remaining_txs, client_info)
            nuevo_score = analysis['score_crediticio']['score']
            nueva_decision = analysis['score_crediticio']['decision']
            nuevo_riesgo = analysis['score_crediticio']['nivel_riesgo']

        return jsonify({
            'success': True,
            'message': f"Se eliminaron {result['transacciones_eliminadas']} movimientos vinculados a '{banco_origen}'. Re-cálculo completado.",
            'transacciones_eliminadas': result['transacciones_eliminadas'],
            'transacciones_restantes': result['transacciones_restantes'],
            'ingresos_restantes': result['ingresos_restantes'],
            'egresos_restantes': result['egresos_restantes'],
            'nuevo_score': nuevo_score,
            'nueva_decision': nueva_decision,
            'nuevo_riesgo': nuevo_riesgo,
            'perfil_key': client_record['perfil_key']
        })

    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/simulate-loan', methods=['POST'])
def simulate_loan():
    """Simula dinámicamente un crédito validando la capacidad de pago del candidato"""
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
            'porcentaje_compromiso': porcentaje_compromiso
        })
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 400


@app.route('/api/upload', methods=['POST'])
def legacy_upload():
    """Subida rápida de estado de cuenta para análisis ad-hoc en simulador"""
    if 'file' not in request.files:
        return jsonify({'success': False, 'error': 'No se envió ningún archivo.'}), 400
    file = request.files['file']
    try:
        filename = file.filename.lower()
        if filename.endswith('.csv'): df = pd.read_csv(file)
        else: df = pd.read_excel(file)

        col_map = {}
        for col in df.columns:
            clean_col = str(col).lower().strip().replace('á', 'a').replace('é', 'e').replace('í', 'i').replace('ó', 'o').replace('ú', 'u')
            if 'fecha' in clean_col or 'date' in clean_col: col_map[col] = 'fecha'
            elif 'monto' in clean_col or 'amount' in clean_col: col_map[col] = 'monto'
            elif 'tipo' in clean_col: col_map[col] = 'tipo'
            elif 'cat' in clean_col: col_map[col] = 'categoria'
            elif 'desc' in clean_col: col_map[col] = 'descripcion'
            elif 'saldo' in clean_col: col_map[col] = 'saldo_resultante'
        df = df.rename(columns=col_map)
        if 'categoria' not in df.columns: df['categoria'] = 'Varios'
        if 'descripcion' not in df.columns: df['descripcion'] = 'Movimiento'
        if 'saldo_resultante' not in df.columns: df['saldo_resultante'] = 1000.0

        transactions = df.to_dict(orient='records')
        client_name = request.form.get('nombre_cliente', 'Cliente Importado')
        client_info = {
            'id': 'IMP-' + str(abs(hash(file.filename)) % 10000),
            'nombre': client_name,
            'rut_dni': request.form.get('rut_dni', 'S/D'),
            'ocupacion': 'Titular de Cuenta',
            'empresa': 'Auditado por Movimientos',
            'tipo_contrato': 'Auditado',
            'antiguedad_laboral_anios': 2.0,
            'antiguedad_bancaria_meses': 12,
            'avatar': 'https://images.unsplash.com/photo-1472099645785-5658abf4ff4e?auto=format&fit=crop&w=150&q=80',
            'etiqueta_perfil': 'Importado vía Archivo'
        }
        analysis = engine.analyze_transactions(transactions, client_info)
        return jsonify({'success': True, 'data': analysis})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500


@app.route('/api/download-template')
def download_template():
    """Descarga plantilla Excel modelo con movimientos de ejemplo"""
    template_data = [
        {'fecha': '2026-05-05', 'descripcion': 'ABONO REMUNERACION SUELDO', 'categoria': 'Nomina/Sueldo', 'tipo': 'INGRESO', 'monto': 2800.0, 'saldo_resultante': 3400.0},
        {'fecha': '2026-05-08', 'descripcion': 'PAGO ARRIENDO / VIVIENDA', 'categoria': 'Servicios/Vivienda', 'tipo': 'EGRESO', 'monto': 800.0, 'saldo_resultante': 2600.0},
        {'fecha': '2026-05-12', 'descripcion': 'CUOTA PRESTAMO BANCARIO VIGENTE', 'categoria': 'Cuota Prestamo', 'tipo': 'EGRESO', 'monto': 220.0, 'saldo_resultante': 2380.0},
        {'fecha': '2026-05-18', 'descripcion': 'SUPERMERCADO Y ALIMENTOS', 'categoria': 'Alimentacion/Supermercado', 'tipo': 'EGRESO', 'monto': 260.0, 'saldo_resultante': 2120.0},
        {'fecha': '2026-06-05', 'descripcion': 'ABONO REMUNERACION SUELDO', 'categoria': 'Nomina/Sueldo', 'tipo': 'INGRESO', 'monto': 2800.0, 'saldo_resultante': 4920.0}
    ]
    df = pd.DataFrame(template_data)
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Movimientos', index=False)
    output.seek(0)
    return send_file(output, as_attachment=True, download_name='plantilla_movimientos_bancarios.xlsx', mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


if __name__ == '__main__':
    print("=" * 72)
    print("  CREDITSENSE - PLATAFORMA DE EVALUACION CREDITICIA MULTI-BANCO")
    print("  Iniciando servidor local en http://127.0.0.1:5000 ...")
    print("=" * 72)
    app.run(host='127.0.0.1', port=5000, debug=True)
