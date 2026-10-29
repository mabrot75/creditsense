"""
Motor de Análisis y Scoring Crediticio Bancario basado en Flujo de Caja (6 meses)
Evalúa el comportamiento de clientes mediante sus movimientos mensuales.
"""

import math
from datetime import datetime
from typing import Dict, List, Any, Optional
import pandas as pd
import numpy as np


class CreditAnalysisEngine:
    def __init__(self):
        # Parámetros y umbrales de política de crédito
        self.MAX_DTI_RECOMMENDED = 0.35  # Máximo 35% del ingreso destinado a deudas
        self.MAX_DTI_TOLERABLE = 0.45    # Límite superior tolerable con condiciones
        
    def analyze_transactions(self, transactions_data: List[Dict[str, Any]], client_info: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Analiza las transacciones de los últimos 6 meses de un cliente y genera el dictamen crediticio.
        """
        df = pd.DataFrame(transactions_data)
        
        # Validar y formatear columnas
        df['fecha'] = pd.to_datetime(df['fecha'])
        df['monto'] = pd.to_numeric(df['monto'], errors='coerce').fillna(0.0)
        df['saldo_resultante'] = pd.to_numeric(df['saldo_resultante'], errors='coerce').fillna(0.0)
        df['tipo'] = df['tipo'].str.upper().str.strip()
        df['categoria'] = df['categoria'].fillna('Otros')
        
        # Ordenar cronológicamente
        df = df.sort_values('fecha').reset_index(drop=True)
        
        # Agrupar por mes (Periodo Año-Mes)
        df['periodo'] = df['fecha'].dt.to_period('M').astype(str)
        periodos = sorted(df['periodo'].unique())
        
        # Si hay más de 6 meses, tomamos los últimos 6
        if len(periodos) > 6:
            periodos = periodos[-6:]
            df = df[df['periodo'].isin(periodos)]
            
        meses_analisis = []
        for p in periodos:
            df_mes = df[df['periodo'] == p]
            
            ingresos_mes = df_mes[df_mes['tipo'] == 'INGRESO']['monto'].sum()
            egresos_mes = df_mes[df_mes['tipo'] == 'EGRESO']['monto'].sum()
            flujo_neto = ingresos_mes - egresos_mes
            tasa_ahorro = (flujo_neto / ingresos_mes) if ingresos_mes > 0 else 0.0
            
            saldo_min = df_mes['saldo_resultante'].min()
            saldo_prom = df_mes['saldo_resultante'].mean()
            
            # Detectar eventos de sobregiro (saldo negativo o comisiones por sobregiro)
            sobregiros_mes = int((df_mes['saldo_resultante'] < 0).sum())
            comisiones_sg = int(df_mes['descripcion'].str.contains('sobregiro|fondos insuficientes|comision saldo negativo', case=False, na=False).sum())
            total_sg_mes = max(sobregiros_mes, comisiones_sg)
            
            # Deuda mensual detectada (categorías de préstamos, cuotas, tarjetas ajenas)
            deuda_mes = df_mes[
                (df_mes['tipo'] == 'EGRESO') & 
                (df_mes['categoria'].str.contains('Prestamo|Cuota|Credito|Deuda', case=False, na=False))
            ]['monto'].sum()
            
            meses_analisis.append({
                'periodo': p,
                'mes_nombre': self._get_month_label(p),
                'ingresos': round(float(ingresos_mes), 2),
                'egresos': round(float(egresos_mes), 2),
                'flujo_neto': round(float(flujo_neto), 2),
                'tasa_ahorro_pct': round(float(tasa_ahorro * 100), 1),
                'saldo_promedio': round(float(saldo_prom), 2),
                'saldo_minimo': round(float(saldo_min), 2),
                'sobregiros': int(total_sg_mes),
                'pagos_deuda': round(float(deuda_mes), 2),
                'transacciones_count': int(len(df_mes))
            })
            
        # Métricas agregadas de los 6 meses
        num_meses = len(meses_analisis) if len(meses_analisis) > 0 else 1
        ingresos_arr = [m['ingresos'] for m in meses_analisis]
        egresos_arr = [m['egresos'] for m in meses_analisis]
        flujos_arr = [m['flujo_neto'] for m in meses_analisis]
        
        ingreso_promedio = float(np.mean(ingresos_arr)) if ingresos_arr else 0.0
        ingreso_std = float(np.std(ingresos_arr)) if ingresos_arr else 0.0
        cv_ingresos = (ingreso_std / ingreso_promedio) if ingreso_promedio > 0 else 1.0  # Coeficiente de variación
        
        egreso_promedio = float(np.mean(egresos_arr)) if egresos_arr else 0.0
        flujo_neto_promedio = float(np.mean(flujos_arr)) if flujos_arr else 0.0
        
        # Tasa de ahorro promedio
        tasa_ahorro_promedio = (flujo_neto_promedio / ingreso_promedio * 100) if ingreso_promedio > 0 else 0.0
        
        # Pagos de deuda promedio mensual
        deudas_arr = [m['pagos_deuda'] for m in meses_analisis]
        deuda_promedio = float(np.mean(deudas_arr)) if deudas_arr else 0.0
        dti_actual = (deuda_promedio / ingreso_promedio) if ingreso_promedio > 0 else 0.0
        
        # Saldos y sobregiros
        saldo_promedio_general = float(np.mean([m['saldo_promedio'] for m in meses_analisis])) if meses_analisis else 0.0
        saldo_minimo_global = float(min([m['saldo_minimo'] for m in meses_analisis])) if meses_analisis else 0.0
        total_sobregiros = sum([m['sobregiros'] for m in meses_analisis])
        meses_deficitarios = sum(1 for m in meses_analisis if m['flujo_neto'] < 0)
        
        # Tendencia de ingresos (comparación primera mitad vs segunda mitad)
        if len(ingresos_arr) >= 4:
            mitad = len(ingresos_arr) // 2
            prom_inicial = np.mean(ingresos_arr[:mitad])
            prom_reciente = np.mean(ingresos_arr[mitad:])
            crecimiento_ingresos_pct = ((prom_reciente - prom_inicial) / prom_inicial * 100) if prom_inicial > 0 else 0.0
        else:
            crecimiento_ingresos_pct = 0.0

        # Desglose de gastos por categoría en los 6 meses
        df_egresos = df[df['tipo'] == 'EGRESO']
        gastos_por_categoria = {}
        if not df_egresos.empty:
            cat_sum = df_egresos.groupby('categoria')['monto'].sum().sort_values(ascending=False)
            total_egresos_totales = df_egresos['monto'].sum()
            for cat, val in cat_sum.items():
                gastos_por_categoria[str(cat)] = {
                    'monto_total': round(float(val), 2),
                    'monto_mensual_prom': round(float(val / num_meses), 2),
                    'porcentaje': round(float((val / total_egresos_totales) * 100), 1) if total_egresos_totales > 0 else 0.0
                }

        # Calcular Score Crediticio y dictamen
        score_details = self._calculate_credit_score(
            ingreso_promedio=ingreso_promedio,
            cv_ingresos=cv_ingresos,
            crecimiento_ingresos_pct=crecimiento_ingresos_pct,
            flujo_neto_promedio=flujo_neto_promedio,
            tasa_ahorro_promedio=tasa_ahorro_promedio,
            saldo_minimo_global=saldo_minimo_global,
            total_sobregiros=total_sobregiros,
            meses_deficitarios=meses_deficitarios,
            dti_actual=dti_actual
        )
        
        # Calcular Capacidad de Endeudamiento y Ofertas
        ofertas = self._calculate_credit_offers(
            score=score_details['score'],
            estado_decision=score_details['decision'],
            ingreso_promedio=ingreso_promedio,
            flujo_neto_promedio=flujo_neto_promedio,
            deuda_promedio=deuda_promedio,
            dti_actual=dti_actual
        )
        
        return {
            'cliente': client_info or {
                'id': 'CLI-001',
                'nombre': 'Cliente Evaluado',
                'rut_dni': '12.345.678-9',
                'ocupacion': 'No especificada',
                'antiguedad_meses': 12
            },
            'resumen_6_meses': {
                'num_meses_analizados': num_meses,
                'ingreso_promedio_mensual': round(ingreso_promedio, 2),
                'egreso_promedio_mensual': round(egreso_promedio, 2),
                'flujo_neto_promedio': round(flujo_neto_promedio, 2),
                'tasa_ahorro_promedio_pct': round(tasa_ahorro_promedio, 1),
                'deuda_actual_mensual': round(deuda_promedio, 2),
                'dti_actual_pct': round(dti_actual * 100, 1),
                'saldo_promedio_global': round(saldo_promedio_general, 2),
                'saldo_minimo_historico': round(saldo_minimo_global, 2),
                'total_sobregiros': total_sobregiros,
                'meses_deficitarios': meses_deficitarios,
                'volatilidad_ingresos_pct': round(cv_ingresos * 100, 1),
                'tendencia_ingresos_pct': round(crecimiento_ingresos_pct, 1)
            },
            'evolucion_mensual': meses_analisis,
            'distribucion_gastos': gastos_por_categoria,
            'score_crediticio': score_details,
            'ofertas': ofertas,
            'fecha_evaluacion': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }

    def _calculate_credit_score(self, ingreso_promedio: float, cv_ingresos: float,
                               crecimiento_ingresos_pct: float, flujo_neto_promedio: float,
                               tasa_ahorro_promedio: float, saldo_minimo_global: float,
                               total_sobregiros: int, meses_deficitarios: int,
                               dti_actual: float) -> Dict[str, Any]:
        """
        Calcula el Score crediticio en una escala bancaria estándar (300 a 850 puntos).
        Descompone los puntos para brindar explicabilidad detallada.
        """
        base_score = 300
        puntos_estabilidad = 0
        puntos_ahorro = 0
        puntos_liquidez = 0
        puntos_deficit = 0
        puntos_endeudamiento = 0
        
        razones_positivas = []
        razones_riesgo = []
        alertas_criticas = []
        
        # 1. Factor Estabilidad y Regularidad de Ingresos (Máximo 150 pts)
        if ingreso_promedio < 400:
            puntos_estabilidad = 20
            razones_riesgo.append("Nivel de ingresos promedio mensual muy bajo (< $400 USD/equivalente).")
        elif cv_ingresos <= 0.10:
            puntos_estabilidad = 150
            razones_positivas.append("Ingresos altamente regulares y estables (volatilidad menor al 10%).")
        elif cv_ingresos <= 0.20:
            puntos_estabilidad = 120
            razones_positivas.append("Buena estabilidad de ingresos mes a mes.")
        elif cv_ingresos <= 0.35:
            puntos_estabilidad = 75
            razones_riesgo.append("Variabilidad moderada en los depósitos mensuales.")
        else:
            puntos_estabilidad = 35
            razones_riesgo.append("Ingresos altamente volátiles o erráticos (variabilidad > 35%).")
            
        # Bonificación por tendencia creciente
        if crecimiento_ingresos_pct > 10:
            puntos_estabilidad = min(150, puntos_estabilidad + 15)
            razones_positivas.append(f"Tendencia positiva de crecimiento en ingresos (+{round(crecimiento_ingresos_pct, 1)}% en últimos meses).")
        elif crecimiento_ingresos_pct < -20:
            puntos_estabilidad = max(0, puntos_estabilidad - 25)
            razones_riesgo.append(f"Caída significativa en los ingresos recientes ({round(crecimiento_ingresos_pct, 1)}%).")

        # 2. Factor Capacidad de Ahorro y Flujo Neto (Máximo 160 pts)
        if tasa_ahorro_promedio >= 30:
            puntos_ahorro = 160
            razones_positivas.append(f"Excelente tasa de ahorro promedio ({round(tasa_ahorro_promedio, 1)}% de sus ingresos).")
        elif tasa_ahorro_promedio >= 18:
            puntos_ahorro = 130
            razones_positivas.append(f"Tasa de ahorro saludable ({round(tasa_ahorro_promedio, 1)}% mensual).")
        elif tasa_ahorro_promedio >= 8:
            puntos_ahorro = 90
            razones_positivas.append("Flujo de caja positivo con margen de ahorro modesto.")
        elif tasa_ahorro_promedio > 0:
            puntos_ahorro = 50
            razones_riesgo.append("Margen de ahorro ajustado (< 8% de los ingresos).")
        else:
            puntos_ahorro = 0
            razones_riesgo.append("Flujo neto promedio negativo (gasta más de lo que ingresa habitualmente).")

        # 3. Factor Comportamiento de Saldo y Sobregiros (Máximo 130 pts)
        if total_sobregiros == 0:
            if saldo_minimo_global >= 500:
                puntos_liquidez = 130
                razones_positivas.append("Mantiene un colchón de seguridad financiero robusto (> $500 en todo momento).")
            elif saldo_minimo_global >= 100:
                puntos_liquidez = 110
                razones_positivas.append("Sin sobregiros ni comisiones por falta de fondos en el periodo.")
            elif saldo_minimo_global >= 0:
                puntos_liquidez = 80
                razones_riesgo.append("Saldos mínimos cercanos a cero pero sin caer en sobregiro.")
        elif total_sobregiros == 1:
            puntos_liquidez = 35
            razones_riesgo.append("Registró 1 evento de sobregiro o saldo negativo en los 6 meses.")
        else:
            puntos_liquidez = 0
            alertas_criticas.append(f"Registró {total_sobregiros} eventos de sobregiro o fondos insuficientes.")

        # 4. Factor Meses Deficitarios (Máximo 60 pts)
        if meses_deficitarios == 0:
            puntos_deficit = 60
            razones_positivas.append("Ningún mes en déficit: 6 meses continuos con superávit de caja.")
        elif meses_deficitarios == 1:
            puntos_deficit = 35
            razones_riesgo.append("Registró 1 mes con flujo neto negativo.")
        elif meses_deficitarios == 2:
            puntos_deficit = 15
            razones_riesgo.append("2 meses con flujo de caja deficitario.")
        else:
            puntos_deficit = 0
            alertas_criticas.append(f"{meses_deficitarios} de los 6 meses registraron déficit de caja.")

        # 5. Factor Endeudamiento Actual (DTI) (Máximo 50 pts)
        if dti_actual <= 0.10:
            puntos_endeudamiento = 50
            razones_positivas.append(f"Nivel de endeudamiento actual muy bajo o nulo ({round(dti_actual * 100, 1)}% DTI).")
        elif dti_actual <= 0.25:
            puntos_endeudamiento = 40
            razones_positivas.append(f"Endeudamiento actual bajo control ({round(dti_actual * 100, 1)}% DTI).")
        elif dti_actual <= 0.38:
            puntos_endeudamiento = 20
            razones_riesgo.append(f"Nivel de endeudamiento preexistente moderado ({round(dti_actual * 100, 1)}% DTI).")
        else:
            puntos_endeudamiento = 0
            alertas_criticas.append(f"Alto compromiso de deuda actual ({round(dti_actual * 100, 1)}% del ingreso ya comprometido).")

        # Suma total del Score (300 a 850)
        puntos_obtenidos = puntos_estabilidad + puntos_ahorro + puntos_liquidez + puntos_deficit + puntos_endeudamiento
        score_final = int(base_score + puntos_obtenidos)
        score_final = min(850, max(300, score_final))

        # Determinar Decision y Nivel de Riesgo
        # Reglas de rechazo crítico por políticas de riesgo
        es_rechazo_forzoso = False
        if total_sobregiros >= 3:
            es_rechazo_forzoso = True
            decision = "RECHAZADO"
            nivel_riesgo = "Alto Riesgo Crítico"
            dictamen = "Rechazado por reiteradas incidencias de sobregiro y fondos insuficientes."
        elif meses_deficitarios >= 4:
            es_rechazo_forzoso = True
            decision = "RECHAZADO"
            nivel_riesgo = "Alto Riesgo Financiero"
            dictamen = "Rechazado debido a que la mayoría de los periodos operó en déficit de caja."
        elif dti_actual >= 0.50:
            es_rechazo_forzoso = True
            decision = "RECHAZADO"
            nivel_riesgo = "Alto Riesgo de Sobreendeudamiento"
            dictamen = "Rechazado por sobrepasar el 50% de capacidad de endeudamiento actual."
        elif score_final >= 720:
            decision = "APROBADO"
            nivel_riesgo = "Bajo Riesgo (Perfil Premium / Excelente)"
            dictamen = "Candidato óptimo. Presenta solvencia comprobada, flujo de caja consistente y alta capacidad de pago."
        elif score_final >= 640:
            decision = "APROBADO"
            nivel_riesgo = "Riesgo Moderado-Bajo (Perfil Estándar)"
            dictamen = "Candidato calificado para líneas estándar. Comportamiento financiero estable."
        elif score_final >= 580:
            decision = "CONDICIONADO"
            nivel_riesgo = "Riesgo Moderado (Requiere Monitoreo / Aval)"
            dictamen = "Aprobación sujeta a condiciones especiales, límites conservadores o presentación de garante."
        else:
            decision = "RECHAZADO"
            nivel_riesgo = "Alto Riesgo"
            dictamen = "Candidato no cumple con los criterios mínimos de riesgo y liquidez institucional."

        # Si fue rechazo forzoso, asegurar que el score refleje el riesgo
        if es_rechazo_forzoso and score_final >= 600:
            score_final = 560

        return {
            'score': score_final,
            'decision': decision,
            'nivel_riesgo': nivel_riesgo,
            'dictamen_resumen': dictamen,
            'desglose_puntos': {
                'base': base_score,
                'estabilidad_ingresos': puntos_estabilidad,
                'capacidad_ahorro': puntos_ahorro,
                'liquidez_sobregiros': puntos_liquidez,
                'meses_deficitarios': puntos_deficit,
                'endeudamiento_dti': puntos_endeudamiento,
                'total_obtenido': score_final
            },
            'razones_positivas': razones_positivas,
            'razones_riesgo': razones_riesgo,
            'alertas_criticas': alertas_criticas
        }

    def _calculate_credit_offers(self, score: int, estado_decision: str,
                                ingreso_promedio: float, flujo_neto_promedio: float,
                                deuda_promedio: float, dti_actual: float) -> Dict[str, Any]:
        """
        Calcula las ofertas pre-aprobadas para Tarjetas de Crédito y Créditos Bancarios
        en función de la capacidad de pago prudencial del cliente.
        """
        # Capacidad de pago mensual libre máxima (35% del ingreso menos deudas actuales)
        capacidad_teorica_35 = (ingreso_promedio * self.MAX_DTI_RECOMMENDED) - deuda_promedio
        # Además no puede superar el 70% del flujo neto real disponible
        capacidad_por_flujo = max(0.0, flujo_neto_promedio * 0.70)
        
        capacidad_pago_mensual = max(0.0, min(capacidad_teorica_35, capacidad_por_flujo))
        capacidad_pago_mensual = round(capacidad_pago_mensual, 2)
        
        if estado_decision == "RECHAZADO" or capacidad_pago_mensual <= 0:
            return {
                'capacidad_cuota_mensual': 0.0,
                'tarjeta_credito': {
                    'elegible': False,
                    'categoria': 'No elegible',
                    'limite_sugerido': 0.0,
                    'color_tarjeta': 'bg-slate-700',
                    'mensaje': 'El perfil actual no califica para emisión de tarjetas de crédito no garantizadas.'
                },
                'credito_bancario': {
                    'elegible': False,
                    'monto_maximo': 0.0,
                    'tasa_anual_tea': 0.0,
                    'plazo_sugerido_meses': 0,
                    'cuota_mensual_estimada': 0.0,
                    'simulaciones': [],
                    'mensaje': 'No se pre-aprueban líneas de crédito debido al nivel de riesgo detectado.'
                }
            }

        # 1. Oferta de Tarjeta de Crédito
        if score >= 750:
            categoria_tc = "Black Signature"
            multiplo = 2.8
            color_tc = "linear-gradient(135deg, #0f172a 0%, #1e293b 50%, #020617 100%)"
            badge_tc = "bg-amber-400 text-slate-900 border-amber-300"
            tasa_tc = 18.5
        elif score >= 680:
            categoria_tc = "Platinum"
            multiplo = 1.9
            color_tc = "linear-gradient(135deg, #334155 0%, #475569 50%, #1e293b 100%)"
            badge_tc = "bg-slate-200 text-slate-800 border-slate-300"
            tasa_tc = 22.0
        elif score >= 630:
            categoria_tc = "Oro"
            multiplo = 1.2
            color_tc = "linear-gradient(135deg, #78350f 0%, #b45309 50%, #d97706 100%)"
            badge_tc = "bg-amber-100 text-amber-800 border-amber-300"
            tasa_tc = 26.5
        else:
            categoria_tc = "Clásica Inicial"
            multiplo = 0.7
            color_tc = "linear-gradient(135deg, #1e3a8a 0%, #1d4ed8 50%, #2563eb 100%)"
            badge_tc = "bg-blue-100 text-blue-800 border-blue-300"
            tasa_tc = 31.0

        limite_tc = round(min(ingreso_promedio * multiplo, capacidad_pago_mensual * 8), -2)
        if limite_tc < 300:
            limite_tc = 300.0

        # 2. Oferta de Crédito Bancario (Préstamo Personal)
        # Tasa de Interés según Score
        if score >= 750:
            tasa_anual = 13.5  # Tasa preferencial 13.5% TEA
            plazo_sugerido = 36
        elif score >= 680:
            tasa_anual = 17.0  # Tasa estándar competitiva
            plazo_sugerido = 24
        elif score >= 630:
            tasa_anual = 22.5  # Tasa de riesgo moderado
            plazo_sugerido = 18
        else:
            tasa_anual = 28.0  # Tasa riesgo alto condicionado
            plazo_sugerido = 12

        # Simulación de montos a diferentes plazos soportables por la cuota máxima
        tasa_mensual = (1 + (tasa_anual / 100.0)) ** (1.0 / 12.0) - 1.0
        
        simulaciones = []
        plazos_evaluar = [12, 24, 36, 48]
        monto_maximo_prestamo = 0.0

        for plazo in plazos_evaluar:
            # Factor de amortización francesa: P = Cuota * [(1 - (1+i)^-n) / i]
            factor = (1.0 - (1.0 + tasa_mensual) ** (-plazo)) / tasa_mensual
            monto_financiable = round(capacidad_pago_mensual * factor, -2)
            
            # Cuota exacta resultante
            cuota_resultante = round(monto_financiable * (tasa_mensual / (1.0 - (1.0 + tasa_mensual) ** (-plazo))), 2)
            
            if plazo == plazo_sugerido:
                monto_maximo_prestamo = monto_financiable
                
            simulaciones.append({
                'plazo_meses': plazo,
                'monto_prestamo': monto_financiable,
                'cuota_mensual': cuota_resultante,
                'interes_total_estimado': round((cuota_resultante * plazo) - monto_financiable, 2),
                'porcentaje_capacidad': round((cuota_resultante / capacidad_pago_mensual * 100), 1) if capacidad_pago_mensual > 0 else 100
            })

        return {
            'capacidad_cuota_mensual': capacidad_pago_mensual,
            'tarjeta_credito': {
                'elegible': True,
                'categoria': categoria_tc,
                'limite_sugerido': limite_tc,
                'tasa_interes_anual_pct': tasa_tc,
                'estilo_css': color_tc,
                'badge_clase': badge_tc,
                'beneficios': self._get_card_perks(categoria_tc)
            },
            'credito_bancario': {
                'elegible': True,
                'monto_maximo_sugerido': monto_maximo_prestamo or (simulaciones[1]['monto_prestamo'] if len(simulaciones) > 1 else 1000.0),
                'plazo_sugerido_meses': plazo_sugerido,
                'tasa_anual_tea_pct': tasa_anual,
                'tasa_mensual_tem_pct': round(tasa_mensual * 100, 2),
                'cuota_mensual_sugerida': round(capacidad_pago_mensual, 2),
                'simulaciones': simulaciones
            }
        }

    def _get_card_perks(self, categoria: str) -> List[str]:
        if "Black" in categoria:
            return ["Salas VIP Lounge en aeropuertos", "Cashback del 3% en todas las compras", "Seguro de viajes de cobertura mundial", "Asistente Concierge 24/7"]
        elif "Platinum" in categoria:
            return ["Cashback del 2% en restaurantes y viajes", "Seguro de compras protegidas", "Membresía bonificada por consumo"]
        elif "Oro" in categoria:
            return ["Puntos bancarios dobles en supermercados", "Protección de precios 30 días", "Cuotas sin interés en comercios asociados"]
        else:
            return ["Compras nacionales e internacionales sin cobro por apertura", "Acceso a banca móvil en tiempo real", "Alertas de fraude inmediatas"]

    def _get_month_label(self, periodo_str: str) -> str:
        """Devuelve un nombre amigable en español para el periodo YYYY-MM"""
        meses = {
            '01': 'Enero', '02': 'Febrero', '03': 'Marzo', '04': 'Abril',
            '05': 'Mayo', '06': 'Junio', '07': 'Julio', '08': 'Agosto',
            '09': 'Septiembre', '10': 'Octubre', '11': 'Noviembre', '12': 'Diciembre'
        }
        partes = periodo_str.split('-')
        if len(partes) == 2:
            anio, mes = partes
            return f"{meses.get(mes, mes)} {anio}"
        return periodo_str
