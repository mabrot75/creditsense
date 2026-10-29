"""
Test integral de endpoints y funcionalidad de la aplicación CreditSense.
"""
import unittest
import json
import os
from app import app

class CreditAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_index_route(self):
        """Verifica que la página principal carga correctamente."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CreditSense', response.data)
        self.assertIn(b'Score Crediticio', response.data)

    def test_get_candidates(self):
        """Verifica el endpoint de lista de candidatos precargados."""
        response = self.app.get('/api/candidates')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 5)
        keys = [c['perfil_key'] for c in data]
        self.assertIn('carlos_excelente', keys)
        self.assertIn('lucia_estable', keys)
        self.assertIn('rodrigo_variable', keys)
        self.assertIn('mariana_endeudada', keys)
        self.assertIn('jorge_sobregirado', keys)

    def test_get_candidate_analysis(self):
        """Verifica el análisis de 6 meses para un candidato específico."""
        response = self.app.get('/api/candidate/carlos_excelente')
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertTrue(data['success'])
        an = data['data']
        self.assertIn('score_crediticio', an)
        self.assertEqual(an['score_crediticio']['decision'], 'APROBADO')
        self.assertEqual(len(an['evolucion_mensual']), 6)
        self.assertIn('ofertas', an)
        self.assertTrue(an['ofertas']['tarjeta_credito']['elegible'])
        self.assertTrue(an['ofertas']['credito_bancario']['elegible'])

    def test_simulate_loan(self):
        """Verifica la simulación interactiva de préstamos bancarios."""
        payload = {
            'monto': 10000.0,
            'plazo_meses': 24,
            'tasa_anual_pct': 16.5,
            'capacidad_maxima': 600.0
        }
        response = self.app.post('/api/simulate-loan',
                                 data=json.dumps(payload),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        res = json.loads(response.data)
        self.assertTrue(res['success'])
        self.assertGreater(res['cuota_mensual'], 0)
        self.assertIn('porcentaje_compromiso', res)

    def test_upload_sample_file(self):
        """Verifica la subida y análisis de un archivo CSV real."""
        sample_dir = os.path.join(os.path.dirname(__file__), 'ejemplos_estados_cuenta')
        files = [f for f in os.listdir(sample_dir) if f.endswith('.csv')]
        self.assertTrue(len(files) > 0, "Debe existir al menos un archivo CSV de prueba.")
        
        target_file = os.path.join(sample_dir, files[0])
        with open(target_file, 'rb') as f:
            response = self.app.post('/api/upload', data={
                'file': (f, files[0]),
                'nombre_cliente': 'Cliente Prueba Test',
                'rut_dni': '11.222.333-4'
            })
        self.assertEqual(response.status_code, 200)
        res = json.loads(response.data)
        self.assertTrue(res['success'])
        self.assertIn('score_crediticio', res['data'])
        self.assertEqual(res['data']['cliente']['nombre'], 'Cliente Prueba Test')

    def test_nuevo_cliente_view(self):
        """Verifica que la vista de registro de nuevo cliente carga correctamente."""
        response = self.app.get('/nuevo-cliente')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Registro de Candidato Crediticio', response.data)

    def test_save_new_client_sqlite(self):
        """Verifica el guardado y persistencia en SQLite de un nuevo cliente con 6 meses de movimientos."""
        payload = {
            'client_info': {
                'nombre': 'Valeria Sofía Rivas',
                'rut_dni': '18.940.123-5',
                'ocupacion': 'Jefa de Proyectos TI',
                'empresa': 'Soluciones Cloud Latam',
                'tipo_contrato': 'Indefinido',
                'antiguedad_laboral_anios': 4.0,
                'antiguedad_bancaria_meses': 36,
                'avatar': 'https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?auto=format&fit=crop&w=150&q=80',
                'etiqueta_perfil': 'Cliente Creado Manualmente'
            },
            'monthly_data': [
                {'periodo': '2026-05', 'ingresos': 3800.0, 'egresos': 2200.0, 'pagos_deuda': 250.0, 'sobregiros': 0},
                {'periodo': '2026-06', 'ingresos': 3800.0, 'egresos': 2150.0, 'pagos_deuda': 250.0, 'sobregiros': 0},
                {'periodo': '2026-07', 'ingresos': 4200.0, 'egresos': 2400.0, 'pagos_deuda': 250.0, 'sobregiros': 0},
                {'periodo': '2026-08', 'ingresos': 3850.0, 'egresos': 2200.0, 'pagos_deuda': 250.0, 'sobregiros': 0},
                {'periodo': '2026-09', 'ingresos': 3900.0, 'egresos': 2100.0, 'pagos_deuda': 250.0, 'sobregiros': 0},
                {'periodo': '2026-10', 'ingresos': 4100.0, 'egresos': 2300.0, 'pagos_deuda': 250.0, 'sobregiros': 0}
            ],
            'saldo_inicial': 3500.0
        }
        response = self.app.post('/api/save-client',
                                 data=json.dumps(payload),
                                 content_type='application/json')
        self.assertEqual(response.status_code, 200)
        res = json.loads(response.data)
        self.assertTrue(res['success'])
        self.assertIn('perfil_key', res)
        perfil_key = res['perfil_key']

        # Verificar que el nuevo cliente ahora aparece en la lista de candidatos
        list_resp = self.app.get('/api/candidates')
        candidates = json.loads(list_resp.data)
        candidate_keys = [c['perfil_key'] for c in candidates]
        self.assertIn(perfil_key, candidate_keys)

        # Verificar que el análisis crediticio se ejecuta exitosamente sobre el cliente guardado
        eval_resp = self.app.get(f'/api/candidate/{perfil_key}')
        self.assertEqual(eval_resp.status_code, 200)
        eval_data = json.loads(eval_resp.data)
        self.assertTrue(eval_data['success'])
        self.assertEqual(eval_data['data']['score_crediticio']['decision'], 'APROBADO')

if __name__ == '__main__':
    unittest.main()
