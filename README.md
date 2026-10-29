# CreditSense — Módulo de Evaluación y Consulta Crediticia Bancaria

Sistema en Python para la **evaluación, scoring y dictamen crediticio de candidatos a tarjetas de crédito y préstamos bancarios**, analizando los movimientos transaccionales y el comportamiento financiero en los **últimos 6 meses**.

---

## 🚀 Inicio Rápido

### Opción 1: Con el lanzador automático (Windows)
Haz doble clic sobre el archivo:
```text
iniciar_modulo_creditos.bat
```
El script iniciará el servidor Flask y abrirá tu navegador automáticamente en `http://127.0.0.1:5000`.

### Opción 2: Desde la terminal / consola
```bash
py modulo_creditos\run.py
```
O directamente con Flask:
```bash
py modulo_creditos\app.py
```

---

## 🆕 Módulo de Alta y Registro de Nuevos Clientes (Base de Datos SQLite)

Ahora puedes registrar clientes desde cero con todas sus variables laborales y financieras:

* **Acceso desde otra ventana:** Haz clic en el botón azul **`+ Registrar Nuevo Cliente`** ubicado en la barra superior del Dashboard o ingresa a `http://127.0.0.1:5000/nuevo-cliente`.
* **Datos solicitados:**
  1. **Personales y Contractuales:** Nombre completo, RUT/DNI, Cargo u ocupación, Empresa empleadora, Tipo de contrato (Indefinido, Plazo Fijo, Honorarios, etc.), Antigüedad laboral en años y Antigüedad con la cuenta bancaria.
  2. **Movimientos de los Últimos 6 Meses:** Tabla intuitiva donde ingresas por cada mes: Total Ingresos ($), Total Egresos ($), Pagos de deudas/cuotas preexistentes ($) y Sobregiros.
  3. **Plantillas Rápidas (1 Clic):** Botones para autocompletar inmediatamente como *Perfil Solvente (A+)*, *Perfil Medio / Freelance*, o *Perfil Sobreendeudado*.
* **Persistencia en Base de Datos:** Al pulsar **"Guardar y Evaluar en Base de Datos"**, el cliente y sus transacciones se almacenan de forma permanente en la base de datos SQLite ([`clientes.db`](file:///c:/Users/Mabrot/OneDrive/Proyecto%20de%20Lectura/modulo_creditos/clientes.db)).
* **Integración inmediata:** El nuevo cliente aparecerá con una insignia destacada (`⭐`) en el selector superior del Dashboard y podrás consultar su Score, ofertas pre-aprobadas y simular créditos al instante.

---

## 🧠 Arquitectura y Metodología de Evaluación

El sistema aplica el principio de **Cashflow Underwriting (Evaluación Crediticia basada en Flujo de Caja Real)**, analizando las transacciones bancarias mes a mes para medir la verdadera solvencia y disciplina financiera del candidato.

### 1. Métricas Clave Auditadas (Periodo de 6 Meses)
* **Ingreso Promedio y Volatilidad ($\sigma / \mu$):** Mide la estabilidad de las fuentes de ingreso (nómina formal vs honorarios o depósitos irregulares).
* **Flujo Neto Mensual ($Ingresos - Egresos$):** Determina si el candidato genera superávit o vive al límite de sus fondos.
* **Tasa de Ahorro Real:** Porcentaje del ingreso mensual que queda como reserva libre.
* **Ratio DTI (Debt-to-Income):** Porcentaje de los ingresos que ya se encuentra comprometido en cuotas de créditos y deudas previas. La política bancaria recomienda un límite prudencial de **35%**.
* **Incidencias de Sobregiro y Saldo Mínimo:** Detección de cuentas en saldo negativo o comisiones por falta de fondos.
* **Tendencia Semestral:** Compara la evolución del primer trimestre frente al segundo para detectar caídas abruptas de liquidez o incrementos patrimoniales.

---

## 📊 Modelo de Scoring Crediticio (300 a 850 Puntos)

El motor calcula un score cuantitativo en la escala estándar de la industria financiera internacional:

| Rango de Score | Clasificación de Riesgo | Dictamen | Ofertas Típicas |
| :--- | :--- | :--- | :--- |
| **750 - 850** | **Excelente / Bajo Riesgo** | **APROBADO** | Tarjeta Black Signature + Crédito Tasa Preferencial (TEA ~13.5%) |
| **680 - 749** | **Bajo Riesgo** | **APROBADO** | Tarjeta Platinum + Crédito Tasa Estándar (TEA ~17.0%) |
| **630 - 679** | **Riesgo Moderado-Bajo** | **APROBADO / CONDICIONADO** | Tarjeta Oro + Crédito Moderado (TEA ~22.5%) |
| **580 - 629** | **Riesgo Moderado** | **CONDICIONADO** | Tarjeta Clásica inicial o Crédito con Garante / Aval |
| **< 580** | **Alto Riesgo** | **RECHAZADO** | No elegible para líneas de crédito sin garantía líquida |

### Desglose de Puntos (Transparencia y Explicabilidad):
* **Puntaje Base:** 300 puntos.
* **Estabilidad y Nivel de Ingresos:** hasta +150 puntos.
* **Capacidad de Ahorro y Flujo Neto:** hasta +160 puntos.
* **Historial de Liquidez y Sobregiros:** hasta +130 puntos.
* **Meses en Superávit vs Déficit:** hasta +60 puntos.
* **Nivel de Endeudamiento Actual (DTI):** hasta +50 puntos.
* *Total Máximo Posible:* **850 puntos**.

---

## 👥 Perfiles de Prueba Preconfigurados (Demostración Inmediata)

En la barra superior de la aplicación puedes alternar instantáneamente entre 5 candidatos con patrones financieros reales:

1. **Carlos Mendoza (Score 850 - Aprobado Black)**:
   * Nómina fija de $4,600 USD/mes, ahorro promedio del 35.9%, 0 sobregiros, DTI del 6.9%.
   * Oferta: Tarjeta Black Signature ($12,800 cupo) y crédito aprobado a tasa preferencial.
2. **Lucía Fernández (Score 820 - Aprobado Platinum)**:
   * Empleada administrativa, ingresos estables de $2,100/mes, ahorro del 24.8%, comportamiento impecable.
3. **Rodrigo Morales (Score 705 - Aprobado Oro)**:
   * Diseñador independiente freelance, ingresos variables mes a mes, ahorro modesto, riesgo controlado.
4. **Mariana Ortiz (Score 515 - Rechazado por Sobreendeudamiento)**:
   * Ingresos adecuados ($2,300), pero paga más de $1,150 en cuotas existentes (DTI > 48%) y 3 meses deficitarios.
5. **Jorge Benítez (Score 560 - Rechazado por Sobregiros)**:
   * Caída de ingresos reciente, 2 sobregiros bancarios con comisiones por saldo insuficiente.

---

## 📁 Carga de Archivos de Movimientos (CSV / Excel)

El módulo permite analizar cualquier estado de cuenta real o simulado.

### Columnas reconocidas automáticamente:
* `fecha` (o `date`): Formato YYYY-MM-DD o estándar de Excel.
* `descripcion` (o `detalle`, `concepto`): Texto explicativo del movimiento.
* `categoria` (o `rubro`): Nómina/Sueldo, Vivienda, Préstamo, Supermercado, Ocio, etc.
* `tipo` (o `type`): `INGRESO` o `EGRESO`.
* `monto` (o `amount`, `importe`): Valor numérico positivo.
* `saldo_resultante` (o `balance`): Saldo tras la operación (opcional, el sistema lo calcula si no viene).

> 💡 Puedes descargar una plantilla lista para usar directamente desde el botón **"Descargar Excel Modelo"** dentro de la ventana de importación.

---

## 🧪 Pruebas Unitarias Automatizadas

El proyecto incluye una suite de pruebas para verificar el funcionamiento del motor y de la API:
```bash
py modulo_creditos\test_app.py
```
Salida esperada: `Ran 5 tests in 0.22s ... OK`.

---

## 🛠️ Estructura del Código

```text
modulo_creditos/
├── app.py                     # Servidor Flask y API REST
├── run.py                     # Script de inicio con apertura de navegador
├── test_app.py                # Suite de pruebas unitarias
├── backend/
│   ├── credit_engine.py       # Motor matemático de análisis y scoring
│   └── sample_data.py         # Generador de perfiles y transacciones demo
├── templates/
│   └── dashboard.html         # Interfaz web interactiva (Tailwind + Chart.js)
├── ejemplos_estados_cuenta/   # Archivos CSV y Excel de prueba listos para importar
└── README.md                  # Este documento
```
