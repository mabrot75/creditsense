"""
Test integral de endpoints y funcionalidad de la plataforma CreditSense.
Cubre Front Principal, Clientes, Carga Multi-Banco y Simulador.
"""
import unittest
import json
import os
from app import app
from backend.database import get_all_clients

class CreditAppTestCase(unittest.TestCase):
    def setUp(self):
        self.app = app.test_client()
        self.app.testing = True

    def test_home_portal_route(self):
        """Verifica que el portal principal (Inicio) carga con los 3 módulos."""
        response = self.app.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'CreditSense', response.data)
        self.assertIn(b'1. Clientes', response.data)
        self.assertIn(b'2. Carga de Movimientos', response.data)
        self.assertIn(b'3. Simulador', response.data)

    def test_clientes_view(self):
        """Verifica que la página de gestión de clientes carga correctamente."""
        response = self.app.get('/clientes')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Cartera de Candidatos', response.data)
        self.assertIn(b'Editar', response.data)

    def test_carga_movimientos_view(self):
        """Verifica que la página de carga multi-banco carga correctamente."""
        response = self.app.get('/carga-movimientos')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Carga y Consolidaci', response.data)
        self.assertIn(b'Acumular movimientos', response.data)

    def test_simulador_view(self):
        """Verifica que el módulo del simulador carga correctamente."""
        response = self.app.get('/simulador')
        self.assertEqual(response.status_code, 200)
        self.assertIn(b'Score Crediticio', response.data)

    def test_client_crud_sqlite(self):
        """Verifica el ciclo completo de creación, edición y eliminación de un cliente."""
        # 1. Crear cliente
        create_payload = {
            'client_info': {
                'id': 'CLI-TEST-99',
                'nombre': 'Cliente Para Editar y Eliminar',
                'rut_dni': '99.888.777-6',
                'ocupacion': 'Especialista QA',
                'empresa': 'Test Labs Inc',
                'tipo_contrato': 'Indefinido',
                'antiguedad_laboral_anios': 2.0,
                'antiguedad_bancaria_meses': 12
            },
            'monthly_data': [
                {'periodo': '2026-05', 'ingresos': 2000.0, 'egresos': 1200.0, 'pagos_deuda': 100.0, 'sobregiros': 0},
                {'periodo': '2026-06', 'ingresos': 2100.0, 'egresos': 1300.0, 'pagos_deuda': 100.0, 'sobregiros': 0}
            ],
            'saldo_inicial': 1000.0
        }
        res_create = self.app.post('/api/save-client', data=json.dumps(create_payload), content_type='application/json')
        self.assertEqual(res_create.status_code, 200)
        perfil_key = json.loads(res_create.data)['perfil_key']

        # 2. Modificar cliente
        update_payload = {
            'client_id': 'CLI-TEST-99',
            'updated_info': {
                'nombre': 'Cliente Editado Correctamente',
                'rut_dni': '99.888.777-6',
                'ocupacion': 'Lead QA Engineer',
                'empresa': 'Enterprise QA Labs',
                'tipo_contrato': 'Indefinido',
                'antiguedad_laboral_anios': 3.5,
                'antiguedad_bancaria_meses': 24,
                'avatar': 'https://example.com/avatar.jpg'
            }
        }
        res_update = self.app.post('/api/client/update', data=json.dumps(update_payload), content_type='application/json')
        self.assertEqual(res_update.status_code, 200)
        self.assertTrue(json.loads(res_update.data)['success'])

        # Verificar cambio
        client_eval = self.app.get(f'/api/candidate/{perfil_key}')
        self.assertEqual(json.loads(client_eval.data)['data']['cliente']['nombre'], 'Cliente Editado Correctamente')

        # 3. Eliminar cliente
        res_delete = self.app.post('/api/client/delete', data=json.dumps({'client_id': 'CLI-TEST-99'}), content_type='application/json')
        self.assertEqual(res_delete.status_code, 200)
        self.assertTrue(json.loads(res_delete.data)['success'])

        # Verificar que ya no existe
        deleted_eval = self.app.get(f'/api/candidate/{perfil_key}')
        self.assertEqual(deleted_eval.status_code, 404)

    def test_upload_bank_movements_accumulation(self):
        """Verifica la carga y acumulación multi-banco de un archivo CSV para un cliente."""
        # Obtener un cliente existente
        clients = get_all_clients()
        target_client = clients[0]
        client_id = target_client['client_info']['id']
        total_tx_antes = target_client['total_transacciones']

        sample_dir = os.path.join(os.path.dirname(__file__), 'ejemplos_estados_cuenta')
        files = [f for f in os.listdir(sample_dir) if f.endswith('.csv')]
        target_file = os.path.join(sample_dir, files[0])

        with open(target_file, 'rb') as f:
            response = self.app.post('/api/upload-bank-movements', data={
                'client_id': client_id,
                'banco_origen': 'Banco de Chile - Cuenta Ahorro',
                'acumular': 'true',
                'file': (f, files[0])
            })
        self.assertEqual(response.status_code, 200)
        res = json.loads(response.data)
        self.assertTrue(res['success'])
        self.assertGreater(res['transacciones_agregadas'], 0)
        self.assertGreater(res['total_transacciones_cliente'], total_tx_antes)

if __name__ == '__main__':
    unittest.main()
