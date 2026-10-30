"""
Manejador de Base de Datos SQLite para Clientes y Transacciones Crediticias.
Almacena y gestiona clientes (CRUD), entidades bancarias vinculadas, edición de nombres de bancos
y eliminación selectiva de movimientos por archivo/banco con re-cálculo financiero continuo.
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

    # Tabla de Transacciones con banco_origen y archivo_origen
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS transacciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        cliente_id TEXT NOT NULL,
        banco_origen TEXT DEFAULT 'Banco Principal',
        archivo_origen TEXT DEFAULT 'Movimientos_Iniciales',
        fecha TEXT NOT NULL,
        descripcion TEXT NOT NULL,
        categoria TEXT NOT NULL,
        tipo TEXT NOT NULL,
        monto REAL NOT NULL,
        saldo_resultante REAL NOT NULL,
        FOREIGN KEY (cliente_id) REFERENCES clientes (id) ON DELETE CASCADE
    )
    """)

    # Migraciones seguras si la base de datos ya existía
    try:
        cursor.execute("ALTER TABLE transacciones ADD COLUMN banco_origen TEXT DEFAULT 'Banco Principal'")
    except sqlite3.OperationalError:
        pass

    try:
        cursor.execute("ALTER TABLE transacciones ADD COLUMN archivo_origen TEXT DEFAULT 'Movimientos_Iniciales'")
    except sqlite3.OperationalError:
        pass

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
                str(tx.get('archivo_origen', 'Movimientos_Iniciales')),
                str(tx.get('fecha', datetime.now().strftime('%Y-%m-%d'))),
                str(tx.get('descripcion', 'Movimiento registrado')),
                str(tx.get('categoria', 'Otros')),
                str(tx.get('tipo', 'EGRESO')).upper(),
                float(tx.get('monto', 0.0)),
                float(tx.get('saldo_resultante', 0.0))
            ))

        cursor.executemany("""
        INSERT INTO transacciones (cliente_id, banco_origen, archivo_origen, fecha, descripcion, categoria, tipo, monto, saldo_resultante)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, tx_tuples)

    conn.commit()

    if should_close:
        conn.close()

    return perfil_key


def update_client_info(client_id: str, updated_info: Dict[str, Any]) -> bool:
    """Modifica los datos personales y laborales de un cliente existente."""
    conn = get_db_connection()
    cursor = conn.cursor()

    avatar_val = updated_info.get('avatar')
    if not avatar_val:
        cursor.execute("SELECT avatar FROM clientes WHERE id = ?", (client_id,))
        row = cursor.fetchone()
        avatar_val = row['avatar'] if row and row['avatar'] else '/static/uploads/avatars/default_avatar.svg'

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
        avatar_val,
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
                                  archivo_origen: str = 'archivo_importado.xlsx',
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
            archivo_origen,
            str(tx.get('fecha', datetime.now().strftime('%Y-%m-%d'))),
            str(tx.get('descripcion', 'Movimiento importado')),
            str(tx.get('categoria', 'Otros')),
            str(tx.get('tipo', 'EGRESO')).upper(),
            float(tx.get('monto', 0.0)),
            float(tx.get('saldo_resultante', 0.0))
        ))

    cursor.executemany("""
    INSERT INTO transacciones (cliente_id, banco_origen, archivo_origen, fecha, descripcion, categoria, tipo, monto, saldo_resultante)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, tx_tuples)

    # Recalcular saldos acumulados cronológicamente
    _recalculate_cumulative_balances(cursor, client_id)

    conn.commit()
    total_added = len(tx_tuples)
    conn.close()
    return total_added


def rename_bank_for_client(client_id: str, old_bank_name: str, new_bank_name: str) -> bool:
    """
    Permite editar y renombrar una entidad bancaria asociada a un cliente,
    actualizando todas sus transacciones vinculadas.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    UPDATE transacciones 
    SET banco_origen = ? 
    WHERE cliente_id = ? AND banco_origen = ?
    """, (new_bank_name.strip(), client_id, old_bank_name.strip()))

    affected = cursor.rowcount
    conn.commit()
    conn.close()
    return affected > 0


def delete_bank_movements(client_id: str, banco_origen: str, archivo_origen: Optional[str] = None) -> Dict[str, Any]:
    """
    Elimina los movimientos de un cliente vinculados a un banco específico y/o archivo,
    y RECALCULA automáticamente los saldos continuos de las transacciones restantes.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    if archivo_origen:
        cursor.execute("""
        DELETE FROM transacciones 
        WHERE cliente_id = ? AND banco_origen = ? AND archivo_origen = ?
        """, (client_id, banco_origen, archivo_origen))
    else:
        cursor.execute("""
        DELETE FROM transacciones 
        WHERE cliente_id = ? AND banco_origen = ?
        """, (client_id, banco_origen))

    deleted_count = cursor.rowcount

    # Recalcular saldos continuos para las transacciones que quedaron
    _recalculate_cumulative_balances(cursor, client_id)
    conn.commit()

    # Obtener totales restantes
    cursor.execute("""
    SELECT 
        COUNT(*) as total_restante,
        COALESCE(SUM(CASE WHEN tipo LIKE '%ING%' THEN monto ELSE 0 END), 0) as ingresos_restantes,
        COALESCE(SUM(CASE WHEN tipo LIKE '%EGR%' THEN monto ELSE 0 END), 0) as egresos_restantes
    FROM transacciones 
    WHERE cliente_id = ?
    """, (client_id,))
    row = cursor.fetchone()

    conn.close()

    return {
        'transacciones_eliminadas': deleted_count,
        'transacciones_restantes': row['total_restante'],
        'ingresos_restantes': round(float(row['ingresos_restantes']), 2),
        'egresos_restantes': round(float(row['egresos_restantes']), 2)
    }


def get_client_banks_and_files(client_id: str) -> List[Dict[str, Any]]:
    """
    Obtiene el desglose de bancos y archivos vinculados a un cliente,
    mostrando conteo de movimientos, ingresos y egresos aportados por cada archivo/banco.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute("""
    SELECT 
        banco_origen,
        archivo_origen,
        COUNT(*) as total_movimientos,
        COALESCE(SUM(CASE WHEN tipo LIKE '%ING%' THEN monto ELSE 0 END), 0) as ingresos,
        COALESCE(SUM(CASE WHEN tipo LIKE '%EGR%' THEN monto ELSE 0 END), 0) as egresos,
        MIN(fecha) as fecha_min,
        MAX(fecha) as fecha_max
    FROM transacciones
    WHERE cliente_id = ?
    GROUP BY banco_origen, archivo_origen
    ORDER BY MAX(fecha) DESC, id DESC
    """, (client_id,))

    rows = cursor.fetchall()
    result = []
    for r in rows:
        result.append({
            'banco_origen': r['banco_origen'] or 'Banco Principal',
            'archivo_origen': r['archivo_origen'] or 'Movimientos_Iniciales',
            'total_movimientos': r['total_movimientos'],
            'ingresos': round(float(r['ingresos']), 2),
            'egresos': round(float(r['egresos']), 2),
            'flujo_neto': round(float(r['ingresos']) - float(r['egresos']), 2),
            'fecha_min': r['fecha_min'],
            'fecha_max': r['fecha_max']
        })

    conn.close()
    return result


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
    SELECT fecha, descripcion, categoria, tipo, monto, saldo_resultante, banco_origen, archivo_origen
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


def get_client_full_data(client_id: str) -> Tuple[Optional[Dict[str, Any]], List[Dict[str, Any]]]:
    """Obtiene toda la información del cliente y sus transacciones consolidadas por ID de cliente."""
    client = get_client_by_id(client_id)
    if not client:
        return None, []
    return get_client_by_key(client['perfil_key'])


def extract_monthly_summary_from_transactions(transactions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Calcula el desglose mensual (ingresos, egresos, deudas, sobregiros) a partir de transacciones."""
    months = {}
    for tx in transactions:
        fecha = str(tx.get('fecha', ''))
        periodo = fecha[:7] if len(fecha) >= 7 else '2026-05'
        if periodo not in months:
            months[periodo] = {
                'periodo': periodo,
                'ingresos': 0.0,
                'egresos': 0.0,
                'pagos_deuda': 0.0,
                'sobregiros': 0
            }

        tipo = str(tx.get('tipo', '')).upper()
        monto = float(tx.get('monto', 0.0))
        cat = str(tx.get('categoria', '')).lower()
        desc = str(tx.get('descripcion', '')).lower()

        if 'ING' in tipo:
            months[periodo]['ingresos'] += monto
        else:
            months[periodo]['egresos'] += monto
            if 'deuda' in cat or 'prestamo' in cat or 'cuota' in desc or 'credito' in cat:
                months[periodo]['pagos_deuda'] += monto
            if 'sobregiro' in cat or 'sobregiro' in desc:
                months[periodo]['sobregiros'] += 1

    result = []
    for p in sorted(months.keys()):
        result.append({
            'periodo': p,
            'ingresos': round(months[p]['ingresos'], 2),
            'egresos': round(months[p]['egresos'], 2),
            'pagos_deuda': round(months[p]['pagos_deuda'], 2),
            'sobregiros': months[p]['sobregiros']
        })
    return result


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
            'banco_origen': 'Banco Principal',
            'archivo_origen': 'Movimientos_Iniciales'
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
                'banco_origen': 'Banco Principal',
                'archivo_origen': 'Movimientos_Iniciales'
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
                'banco_origen': 'Banco Principal',
                'archivo_origen': 'Movimientos_Iniciales'
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
                'banco_origen': 'Banco Principal',
                'archivo_origen': 'Movimientos_Iniciales'
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
                'banco_origen': 'Banco Principal',
                'archivo_origen': 'Movimientos_Iniciales'
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
                    'banco_origen': 'Banco Principal',
                    'archivo_origen': 'Movimientos_Iniciales'
                })

    return transactions
