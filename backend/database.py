"""
Manejador de Base de Datos SQLite para Clientes y Transacciones Crediticias.
Almacena y gestiona los clientes precargados y los nuevos clientes registrados desde la interfaz.
"""

import os
import sqlite3
from datetime import datetime, timedelta
import random
from typing import Dict, List, Tuple, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'clientes.db')


def get_db_connection():
    """Retorna una conexión a la base de datos SQLite con row_factory para diccionarios."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa las tablas de SQLite y precarga los 5 candidatos demo si la base de datos está vacía."""
    conn = get_db_connection()
    cursor = conn.cursor()

    # Tabla de Clientes
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS clientes (
        id TEXT PRIMARY KEY,
        perfil_key TEXT UNIQUE NOT NULL,
        nombre TEXT NOT NULL,
        rut_dni TEXT NOT NULL,
        ocupacion TEXT NOT NULL,
        empresa TEXT,
        tipo_contrato TEXT,
        antiguedad_laboral_anios REAL,
        antiguedad_bancaria_meses INTEGER,
        avatar TEXT,
        etiqueta_perfil TEXT,
        es_personalizado INTEGER DEFAULT 0,
        fecha_creacion TEXT
    )
    """)

    # Tabla de Transacciones
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id TEXT NOT NULL,
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        categoria TEXT NOT NULL,
        tipo TEXT NOT NULL,
        monto REAL NOT NULL,
        saldo_resultante REAL NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
    )
    """)

    conn.commit()

    # Verificar si ya existen clientes; si no, poblar con los 5 perfiles demo de sample_data
    cursor.execute("SELECT COUNT(*) AS total FROM clientes")
    count = cursor.fetchone()['total']

    if count == 0:
        seed_demo_candidates(conn)

    conn.close()


def seed_demo_candidates(conn):
    """Puebla la base de datos con los 5 candidatos demo iniciales."""
    from backend.sample_data import generate_candidate_transactions

    demo_keys = ['carlos_excelente', 'lucia_estable', 'rodrigo_variable', 'mariana_endeudada', 'jorge_sobregirado']
    
    for key in demo_keys:
        client_info, txs = generate_candidate_transactions(key)
        save_client_to_db(client_info, txs, perfil_key=key, es_personalizado=0, conn=conn)

    print("[DB] 5 candidatos demo precargados en la base de datos SQLite.")


def save_client_to_db(client_info: Dict[str, Any], transactions: List[Dict[str, Any]], 
                       perfil_key: Optional[str] = None, es_personalizado: int = 1,
                       conn: Optional[sqlite3.Connection] = None) -> str:
    """
    Inserta o actualiza un cliente y su historial de transacciones en la base de datos SQLite.
    """
    should_close = False
    if conn is None:
        conn = get_db_connection()
        should_close = True

    cursor = conn.cursor()

    client_id = client_info.get('id') or f"CLI-{random.randint(2000, 9999)}"
    if not perfil_key:
        clean_name = client_info['nombre'].lower().replace(' ', '_')
        perfil_key = f"usr_{clean_name}_{client_id.replace('-', '_')}"

    # Guardar / Actualizar cliente
    cursor.execute("""
    INSERT OR REPLACE INTO clientes (
        id, perfil_key, nombre, rut_dni, ocupacion, empresa,
        tipo_contrato, antiguedad_laboral_anios, antiguedad_bancaria_meses,
        avatar, etiqueta_perfil, es_personalizado, fecha_creacion
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        client_id,
        perfil_key,
        client_info.get('nombre', 'Nuevo Cliente'),
        client_info.get('rut_dni', 'S/D'),
        client_info.get('ocupacion', 'No especificada'),
        client_info.get('empresa', 'No especificada'),
        client_info.get('tipo_contrato', 'Indefinido'),
        float(client_info.get('antiguedad_laboral_anios', 1.0)),
        int(client_info.get('antiguedad_bancaria_meses', 12)),
        client_info.get('avatar', 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&w=150&q=80'),
        client_info.get('etiqueta_perfil', 'Cliente Creado Manualmente'),
        es_personalizado,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))

    # Eliminar transacciones anteriores de este cliente si existían
    cursor.execute("DELETE FROM transacciones WHERE cliente_id = ?", (client_id,))

    # Insertar transacciones
    tx_tuples = []
    for tx in transactions:
        tx_tuples.append((
            client_id,
            str(tx.get('fecha', datetime.now().strftime('%Y-%m-%d'))),
            str(tx.get('descripcion', 'Movimiento registrado')),
            str(tx.get('categoria', 'Otros')),
            str(tx.get('tipo', 'EGRESO')).upper(),
            float(tx.get('monto', 0.0)),
            float(tx.get('saldo_resultante', 0.0))
        ))

    cursor.executemany("""
    INSERT INTO transacciones (cliente_id, fecha, descripcion, categoria, tipo, monto, saldo_resultante)
    VALUES (?, ?, ?, ?, ?, ?, ?)
    """, tx_tuples)

    conn.commit()

    if should_close:
        conn.close()

    return perfil_key


def get_all_clients() -> List[Dict[str, Any]]:
    """Devuelve la lista de todos los candidatos registrados en la base de datos."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT c.*, COUNT(t.id) as total_transacciones 
    FROM clientes c
    LEFT JOIN transacciones t ON c.id = t.cliente_id
    GROUP BY c.id
    ORDER BY c.es_personalizado DESC, c.fecha_creacion DESC
    """)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        result.append({
            'perfil_key': row['perfil_key'],
            'client_info': {
                'id': row['id'],
                'nombre': row['nombre'],
                'rut_dni': row['rut_dni'],
                'ocupacion': row['ocupacion'],
                'empresa': row['empresa'],
                'tipo_contrato': row['tipo_contrato'],
                'antiguedad_laboral_anios': row['antiguedad_laboral_anios'],
                'antiguedad_bancaria_meses': row['antiguedad_bancaria_meses'],
                'avatar': row['avatar'],
                'etiqueta_perfil': row['etiqueta_perfil'],
                'es_personalizado': bool(row['es_personalizado'])
            },
            'total_transacciones': row['total_transacciones']
        })

    conn.close()
    return result


def get_client_by_key(perfil_key: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Obtiene un cliente y todas sus transacciones a partir de su perfil_key."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clientes WHERE perfil_key = ?", (perfil_key,))
    client_row = cursor.fetchone()

    if not client_row:
        conn.close()
        return None, []

    client_info = {
        'id': client_row['id'],
        'nombre': client_row['nombre'],
        'rut_dni': client_row['rut_dni'],
        'ocupacion': client_row['ocupacion'],
        'empresa': client_row['empresa'],
        'tipo_contrato': client_row['tipo_contrato'],
        'antiguedad_laboral_anios': client_row['antiguedad_laboral_anios'],
        'antiguedad_bancaria_meses': client_row['antiguedad_bancaria_meses'],
        'avatar': client_row['avatar'],
        'etiqueta_perfil': client_row['etiqueta_perfil'],
        'es_personalizado': bool(client_row['es_personalizado'])
    }

    cursor.execute("""
    SELECT fecha, descripcion, categoria, tipo, monto, saldo_resultante 
    FROM transacciones 
    WHERE cliente_id = ? 
    ORDER BY fecha ASC, id ASC
    """, (client_row['id'],))
    tx_rows = cursor.fetchall()

    transactions = [dict(tx) for tx in tx_rows]

    conn.close()
    return client_info, transactions


def generate_transactions_from_monthly_inputs(monthly_data: List[Dict[str, Any]], initial_balance: float = 1000.0) -> List[Dict[str, Any]]:
    """
    Convierte una serie de 6 registros mensuales ingresados en formulario en un conjunto
    de transacciones diarias realistas compatibles al 100% con el motor de crédito.
    """
    transactions = []
    running_balance = float(initial_balance)

    for m in monthly_data:
        periodo = m['periodo']  # 'YYYY-MM'
        ingresos_total = float(m.get('ingresos', 0.0))
        egresos_total = float(m.get('egresos', 0.0))
        deuda_mensual = float(m.get('pagos_deuda', 0.0))
        sobregiros = int(m.get('sobregiros', 0))

        # Fechas del mes
        try:
            year, month = map(int, periodo.split('-'))
        except:
            year, month = 2026, 5

        # 1. Depósito de Nómina / Ingreso principal (Día 5 o 28)
        running_balance += ingresos_total
        transactions.append({
            'fecha': f"{year:04d}-{month:02d}-05",
            'descripcion': 'ABONO REMUNERACION / INGRESO MENSUAL',
            'categoria': 'Nomina/Sueldo',
            'tipo': 'INGRESO',
            'monto': round(ingresos_total, 2),
            'saldo_resultante': round(running_balance, 2)
        })

        # 2. Pago de Vivienda / Arriendo (Día 8)
        gasto_vivienda = round(min(egresos_total * 0.35, egresos_total), 2)
        if gasto_vivienda > 0:
            running_balance -= gasto_vivienda
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-08",
                'descripcion': 'PAGO VIVIENDA / ARRIENDO / SERVICIOS',
                'categoria': 'Servicios/Vivienda',
                'tipo': 'EGRESO',
                'monto': gasto_vivienda,
                'saldo_resultante': round(running_balance, 2)
            })

        # 3. Pago de Cuota de Crédito / Deuda (si aplica, Día 12)
        if deuda_mensual > 0:
            running_balance -= deuda_mensual
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-12",
                'descripcion': 'CUOTA PRESTAMO / COMPROMISO FINANCIERO',
                'categoria': 'Cuota Prestamo',
                'tipo': 'EGRESO',
                'monto': round(deuda_mensual, 2),
                'saldo_resultante': round(running_balance, 2)
            })

        # 4. Supermercado y alimentación (Día 16)
        resto_egresos = max(0.0, egresos_total - gasto_vivienda - deuda_mensual)
        gasto_super = round(resto_egresos * 0.60, 2)
        if gasto_super > 0:
            running_balance -= gasto_super
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-16",
                'descripcion': 'COMPRA SUPERMERCADOS Y ALIMENTOS',
                'categoria': 'Alimentacion/Supermercado',
                'tipo': 'EGRESO',
                'monto': gasto_super,
                'saldo_resultante': round(running_balance, 2)
            })

        # 5. Ocio y gastos varios (Día 24)
        gasto_varios = round(max(0.0, resto_egresos - gasto_super), 2)
        if gasto_varios > 0:
            running_balance -= gasto_varios
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-24",
                'descripcion': 'GASTOS VARIOS / CONSUMO COMERCIAL',
                'categoria': 'Compras Tarjeta',
                'tipo': 'EGRESO',
                'monto': gasto_varios,
                'saldo_resultante': round(running_balance, 2)
            })

        # 6. Eventos de sobregiro si fueron especificados
        if sobregiros > 0:
            # Forzar saldo negativo y registrar comisión
            if running_balance > 0:
                running_balance = -50.0
            else:
                running_balance -= 60.0
                
            for s in range(sobregiros):
                transactions.append({
                    'fecha': f"{year:04d}-{month:02d}-27",
                    'descripcion': f'COMISION POR SOBREGIRO / FONDOS INSUFICIENTES #{s+1}',
                    'categoria': 'Sobregiro/Comision',
                    'tipo': 'EGRESO',
                    'monto': 35.0,
                    'saldo_resultante': round(running_balance, 2)
                })

    return transactions
