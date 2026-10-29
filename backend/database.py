"""
Manejador de Base de Datos SQLite para Clientes y Transacciones Crediticias.
Almacena y gestiona clientes (creación, edición, eliminación) y acumulación multi-banco de movimientos.
"""

import os
import sqlite3
from datetime import datetime
import random
from typing import Dict, List, Tuple, Any, Optional

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'clientes.db')


def get_db_connection():
    """Retorna una conexión a la base de datos SQLite con row_factory para diccionarios."""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    """Inicializa las tablas de SQLite y migra columnas si es necesario."""
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

    # Tabla de Transacciones con columna banco_origen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id TEXT NOT NULL,
        banco_origen TEXT DEFAULT 'Banco Principal',
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        categoria TEXT NOT NULL,
        tipo TEXT NOT NULL,
        monto REAL NOT NULL,
        saldo_resultante REAL NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
    )
    """)

    # Migración: asegurar que la columna banco_origen exista en transacciones
    try:
        cursor.execute("ALTER TABLE transacciones ADD COLUMN banco_origen TEXT DEFAULT 'Banco Principal'")
    except sqlite3.OperationalError:
        pass  # Ya existe la columna

    conn.commit()

    # Verificar si ya existen clientes; si no, poblar con los 5 perfiles demo
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
        clean_name = client_info.get('nombre', 'cliente').lower().replace(' ', '_')
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
        client_info.get('etiqueta_perfil', 'Cliente Registrado'),
        es_personalizado,
        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    ))

    # Eliminar transacciones anteriores de este cliente si existían
    cursor.execute("DELETE FROM transacciones WHERE cliente_id = ?", (client_id,))

    # Insertar transacciones
    if transactions:
        tx_tuples = []
        for tx in transactions:
            tx_tuples.append((
                client_id,
                str(tx.get('banco_origen', 'Banco Principal')),
                str(tx.get('fecha', datetime.now().strftime('%Y-%m-%d'))),
                str(tx.get('descripcion', 'Movimiento registrado')),
                str(tx.get('categoria', 'Otros')),
                str(tx.get('tipo', 'EGRESO')).upper(),
                float(tx.get('monto', 0.0)),
                float(tx.get('saldo_resultante', 0.0))
            ))

        cursor.executemany("""
        INSERT INTO transacciones (cliente_id, banco_origen, fecha, descripcion, categoria, tipo, monto, saldo_resultante)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, tx_tuples)

    conn.commit()

    if should_close:
        conn.close()

    return perfil_key


def update_client_info(client_id: str, updated_info: Dict[str, Any]) -> bool:
    """Modifica los datos personales y laborales de un cliente existente."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE clientes SET
        nombre = ?,
        rut_dni = ?,
        ocupacion = ?,
        empresa = ?,
        tipo_contrato = ?,
        antiguedad_laboral_anios = ?,
        antiguedad_bancaria_meses = ?,
        avatar = ?
    WHERE id = ?
    """, (
        updated_info.get('nombre'),
        updated_info.get('rut_dni'),
        updated_info.get('ocupacion'),
        updated_info.get('empresa'),
        updated_info.get('tipo_contrato'),
        float(updated_info.get('antiguedad_laboral_anios', 1.0)),
        int(updated_info.get('antiguedad_bancaria_meses', 12)),
        updated_info.get('avatar'),
        client_id
    ))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def delete_client_by_id(client_id: str) -> bool:
    """Elimina permanentemente a un cliente y todas sus transacciones asociadas."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("DELETE FROM transacciones WHERE cliente_id = ?", (client_id,))
    cursor.execute("DELETE FROM clientes WHERE id = ?", (client_id,))

    success = cursor.rowcount > 0
    conn.commit()
    conn.close()
    return success


def append_transactions_to_client(client_id: str, new_transactions: List[Dict[str, Any]], 
                                  banco_origen: str = 'Banco Adicional', 
                                  reemplazar: bool = False) -> int:
    """
    Acumula / consolida movimientos de un nuevo banco o archivo al historial existente del cliente.
    Si reemplazar=True, vacía los movimientos anteriores y coloca solo los nuevos.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if reemplazar:
        cursor.execute("DELETE FROM transacciones WHERE cliente_id = ?", (client_id,))

    tx_tuples = []
    for tx in new_transactions:
        tx_tuples.append((
            client_id,
            banco_origen,
            str(tx.get('fecha', datetime.now().strftime('%Y-%m-%d'))),
            str(tx.get('descripcion', 'Movimiento importado')),
            str(tx.get('categoria', 'Otros')),
            str(tx.get('tipo', 'EGRESO')).upper(),
            float(tx.get('monto', 0.0)),
            float(tx.get('saldo_resultante', 0.0))
        ))

    cursor.executemany("""
    INSERT INTO transacciones (cliente_id, banco_origen, fecha, descripcion, categoria, tipo, monto, saldo_resultante)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, tx_tuples)

    # Recalcular saldos acumulados cronológicamente
    _recalculate_cumulative_balances(cursor, client_id)

    conn.commit()
    total_added = len(tx_tuples)
    conn.close()
    return total_added


def _recalculate_cumulative_balances(cursor, client_id: str):
    """Ordena cronológicamente todas las transacciones del cliente y recalcula el saldo continuo resultante."""
    cursor.execute("""
    SELECT id, tipo, monto 
    FROM transacciones 
    WHERE cliente_id = ? 
    ORDER BY fecha ASC, id ASC
    """, (client_id,))
    rows = cursor.fetchall()

    balance = 1500.0  # Base inicial estimada
    for r in rows:
        m = float(r['monto'])
        t = str(r['tipo']).upper()
        if 'ING' in t:
            balance += m
        else:
            balance -= m
        cursor.execute("UPDATE transacciones SET saldo_resultante = ? WHERE id = ?", (round(balance, 2), r['id']))


def get_all_clients() -> List[Dict[str, Any]]:
    """Devuelve la lista de todos los candidatos registrados con conteo de transacciones y bancos asociados."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT c.*, 
           COUNT(t.id) as total_transacciones,
           GROUP_CONCAT(DISTINCT t.banco_origen) as bancos_asociados
    FROM clientes c
    LEFT JOIN transacciones t ON c.id = t.cliente_id
    GROUP BY c.id
    ORDER BY c.es_personalizado DESC, c.fecha_creacion DESC
    """)
    rows = cursor.fetchall()

    result = []
    for row in rows:
        bancos_str = row['bancos_asociados'] or 'Banco Principal'
        bancos_list = [b.strip() for b in bancos_str.split(',') if b.strip()]
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
                'es_personalizado': bool(row['es_personalizado']),
                'bancos': bancos_list
            },
            'total_transacciones': row['total_transacciones']
        })

    conn.close()
    return result


def get_client_by_key(perfil_key: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Obtiene un cliente y todas sus transacciones consolidadas a partir de su perfil_key."""
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM clientes WHERE perfil_key = ?", (perfil_key,))
    client_row = cursor.fetchone()

    if not client_row:
        conn.close()
        return None, []

    cursor.execute("""
    SELECT fecha, descripcion, categoria, tipo, monto, saldo_resultante, banco_origen
    FROM transacciones 
    WHERE cliente_id = ? 
    ORDER BY fecha ASC, id ASC
    """, (client_row['id'],))
    tx_rows = cursor.fetchall()

    bancos = list(set([r['banco_origen'] for r in tx_rows if r['banco_origen']]))
    if not bancos:
        bancos = ['Banco Principal']

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
        'es_personalizado': bool(client_row['es_personalizado']),
        'bancos': bancos
    }

    transactions = [dict(tx) for tx in tx_rows]
    conn.close()
    return client_info, transactions


def get_client_by_id(client_id: str) -> Optional[Dict[str, Any]]:
    """Obtiene un cliente por su ID único."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM clientes WHERE id = ?", (client_id,))
    row = cursor.fetchone()
    conn.close()
    if row:
        return dict(row)
    return None


def generate_transactions_from_monthly_inputs(monthly_data: List[Dict[str, Any]], initial_balance: float = 1000.0) -> List[Dict[str, Any]]:
    """
    Convierte registros mensuales en transacciones diarias realistas compatibles al 100% con el motor de crédito.
    """
    transactions = []
    running_balance = float(initial_balance)

    for m in monthly_data:
        periodo = m['periodo']  # 'YYYY-MM'
        ingresos_total = float(m.get('ingresos', 0.0))
        egresos_total = float(m.get('egresos', 0.0))
        deuda_mensual = float(m.get('pagos_deuda', 0.0))
        sobregiros = int(m.get('sobregiros', 0))

        try:
            year, month = map(int, periodo.split('-'))
        except:
            year, month = 2026, 5

        # 1. Ingreso / Sueldo
        running_balance += ingresos_total
        transactions.append({
            'fecha': f"{year:04d}-{month:02d}-05",
            'descripcion': 'ABONO REMUNERACION / SUELDO MENSUAL',
            'categoria': 'Nomina/Sueldo',
            'tipo': 'INGRESO',
            'monto': round(ingresos_total, 2),
            'saldo_resultante': round(running_balance, 2),
            'banco_origen': 'Banco Principal'
        })

        # 2. Vivienda
        gasto_vivienda = round(min(egresos_total * 0.35, egresos_total), 2)
        if gasto_vivienda > 0:
            running_balance -= gasto_vivienda
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-08",
                'descripcion': 'PAGO VIVIENDA / ARRIENDO / SERVICIOS',
                'categoria': 'Servicios/Vivienda',
                'tipo': 'EGRESO',
                'monto': gasto_vivienda,
                'saldo_resultante': round(running_balance, 2),
                'banco_origen': 'Banco Principal'
            })

        # 3. Cuota Crédito
        if deuda_mensual > 0:
            running_balance -= deuda_mensual
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-12",
                'descripcion': 'CUOTA PRESTAMO / COMPROMISO BANCARIO',
                'categoria': 'Cuota Prestamo',
                'tipo': 'EGRESO',
                'monto': round(deuda_mensual, 2),
                'saldo_resultante': round(running_balance, 2),
                'banco_origen': 'Banco Principal'
            })

        # 4. Supermercado
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
                'saldo_resultante': round(running_balance, 2),
                'banco_origen': 'Banco Principal'
            })

        # 5. Ocio / Tarjeta
        gasto_varios = round(max(0.0, resto_egresos - gasto_super), 2)
        if gasto_varios > 0:
            running_balance -= gasto_varios
            transactions.append({
                'fecha': f"{year:04d}-{month:02d}-24",
                'descripcion': 'GASTOS VARIOS / CONSUMO COMERCIAL',
                'categoria': 'Compras Tarjeta',
                'tipo': 'EGRESO',
                'monto': gasto_varios,
                'saldo_resultante': round(running_balance, 2),
                'banco_origen': 'Banco Principal'
            })

        # 6. Sobregiros
        if sobregiros > 0:
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
                    'saldo_resultante': round(running_balance, 2),
                    'banco_origen': 'Banco Principal'
                })

    return transactions
