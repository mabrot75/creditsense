"""
Test integral de endpoints y funcionalidad de la plataforma CreditSense.
Cubre Front Principal, Clientes, Carga Multi-Banco y Simulador.
"""
import unittest
import json
import os
import io
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

    def test_client_banks_list_rename_and_delete_with_recalculation(self):
        """Verifica listar bancos, renombrar un banco, y eliminar movimientos por archivo con recálculo."""
        # 1. Crear un cliente con transacciones iniciales en 'Banco Alfa'
        create_payload = {
            'client_info': {
                'id': 'CLI-TEST-BANKS-01',
                'nombre': 'Cliente MultiBanco Test',
                'rut_dni': '11.222.333-4',
                'ocupacion': 'Ingeniero de Datos',
                'empresa': 'Data Corp',
                'tipo_contrato': 'Indefinido',
                'antiguedad_laboral_anios': 4.0,
                'antiguedad_bancaria_meses': 36
            },
            'monthly_data': [
                {'periodo': '2026-01', 'ingresos': 3000.0, 'egresos': 1500.0, 'pagos_deuda': 200.0, 'sobregiros': 0},
                {'periodo': '2026-02', 'ingresos': 3000.0, 'egresos': 1500.0, 'pagos_deuda': 200.0, 'sobregiros': 0},
                {'periodo': '2026-03', 'ingresos': 3000.0, 'egresos': 1500.0, 'pagos_deuda': 200.0, 'sobregiros': 0},
                {'periodo': '2026-04', 'ingresos': 3000.0, 'egresos': 1500.0, 'pagos_deuda': 200.0, 'sobregiros': 0},
                {'periodo': '2026-05', 'ingresos': 3000.0, 'egresos': 1500.0, 'pagos_deuda': 200.0, 'sobregiros': 0},
                {'periodo': '2026-06', 'ingresos': 3000.0, 'egresos': 1500.0, 'pagos_deuda': 200.0, 'sobregiros': 0}
            ],
            'saldo_inicial': 2000.0
        }
        res_create = self.app.post('/api/save-client', data=json.dumps(create_payload), content_type='application/json')
        self.assertEqual(res_create.status_code, 200)

        # 2. Consultar entidades bancarias vinculadas
        res_banks = self.app.get('/api/client/CLI-TEST-BANKS-01/banks')
        self.assertEqual(res_banks.status_code, 200)
        banks_data = json.loads(res_banks.data)
        self.assertTrue(banks_data['success'])
        self.assertGreater(len(banks_data['banks']), 0)
        initial_bank_name = banks_data['banks'][0]['banco_origen']
        initial_file_name = banks_data['banks'][0]['archivo_origen']

        # 3. Renombrar banco de 'Banco Principal' (o nombre inicial) a 'Banco Santander Central'
        res_rename = self.app.post('/api/client/rename-bank', data=json.dumps({
            'client_id': 'CLI-TEST-BANKS-01',
            'old_bank_name': initial_bank_name,
            'new_bank_name': 'Banco Santander Central'
        }), content_type='application/json')
        self.assertEqual(res_rename.status_code, 200)
        self.assertTrue(json.loads(res_rename.data)['success'])

        # Verificar que la lista de bancos ahora refleja 'Banco Santander Central'
        res_banks_after = self.app.get('/api/client/CLI-TEST-BANKS-01/banks')
        banks_after_data = json.loads(res_banks_after.data)
        bank_names = [b['banco_origen'] for b in banks_after_data['banks']]
        self.assertIn('Banco Santander Central', bank_names)
        self.assertNotIn(initial_bank_name, bank_names)

        # 4. Eliminar los movimientos vinculados a ese banco y archivo, validando el recálculo
        res_delete_movs = self.app.post('/api/client/delete-bank-movements', data=json.dumps({
            'client_id': 'CLI-TEST-BANKS-01',
            'banco_origen': 'Banco Santander Central',
            'archivo_origen': initial_file_name
        }), content_type='application/json')
        self.assertEqual(res_delete_movs.status_code, 200)
        delete_movs_data = json.loads(res_delete_movs.data)
        self.assertTrue(delete_movs_data['success'])
        self.assertGreater(delete_movs_data['transacciones_eliminadas'], 0)
        self.assertEqual(delete_movs_data['transacciones_restantes'], 0)
        self.assertEqual(delete_movs_data['ingresos_restantes'], 0.0)
        self.assertEqual(delete_movs_data['egresos_restantes'], 0.0)
        self.assertEqual(delete_movs_data['nuevo_score'], 0)
        self.assertEqual(delete_movs_data['nueva_decision'], 'SIN_DATOS')

        # 5. Limpieza: Eliminar cliente de prueba
        self.app.post('/api/client/delete', data=json.dumps({'client_id': 'CLI-TEST-BANKS-01'}), content_type='application/json')

    def test_avatar_upload_and_full_profile_edit(self):
        """Verifica la subida de foto de avatar, consulta de perfil completo y edición persistente en base de datos."""
        # 1. Probar endpoint /api/upload-avatar con un archivo de imagen en memoria
        dummy_png = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15c4\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xb4\x00\x00\x00\x00IEND\xaeB`\x82'
        upload_resp = self.app.post('/api/upload-avatar', data={
            'avatar': (io.BytesIO(dummy_png), 'mi_foto_cliente.png')
        })
        self.assertEqual(upload_resp.status_code, 200)
        upload_data = json.loads(upload_resp.data)
        self.assertTrue(upload_data['success'])
        avatar_url = upload_data['avatar_url']
        self.assertTrue(avatar_url.startswith('/static/uploads/avatars/avatar_'))

        # 2. Crear cliente con ese avatar
        client_id = 'CLI-TEST-AVATAR-99'
        create_payload = {
            'client_info': {
                'id': client_id,
                'nombre': 'Cliente Con Foto Personalizada',
                'rut_dni': '15.678.901-2',
                'ocupacion': 'Arquitecto de Software',
                'empresa': 'Tech Solutions SpA',
                'tipo_contrato': 'Indefinido',
                'antiguedad_laboral_anios': 5.0,
                'antiguedad_bancaria_meses': 48,
                'avatar': avatar_url
            },
            'monthly_data': [
                {'periodo': '2026-05', 'ingresos': 4000.0, 'egresos': 2000.0, 'pagos_deuda': 300.0, 'sobregiros': 0},
                {'periodo': '2026-06', 'ingresos': 4200.0, 'egresos': 2100.0, 'pagos_deuda': 300.0, 'sobregiros': 0}
            ],
            'saldo_inicial': 3000.0
        }
        res_create = self.app.post('/api/save-client', data=json.dumps(create_payload), content_type='application/json')
        self.assertEqual(res_create.status_code, 200)

        # 3. Consultar perfil completo del cliente vía GET /api/client/<client_id>
        res_get = self.app.get(f'/api/client/{client_id}')
        self.assertEqual(res_get.status_code, 200)
        client_data = json.loads(res_get.data)
        self.assertTrue(client_data['success'])
        self.assertEqual(client_data['client']['avatar'], avatar_url)
        self.assertGreater(len(client_data['monthly_summary']), 0)

        # 4. Modificar el perfil completo cambiando ocupación y seleccionando otra foto/avatar
        new_avatar_url = '/static/uploads/avatars/avatar_female_2.svg'
        update_payload = {
            'client_id': client_id,
            'updated_info': {
                'nombre': 'Cliente Con Foto Actualizada',
                'rut_dni': '15.678.901-2',
                'ocupacion': 'CTO & VP Engineering',
                'empresa': 'Enterprise Tech Latam',
                'tipo_contrato': 'Empresario / Dueño',
                'antiguedad_laboral_anios': 6.5,
                'antiguedad_bancaria_meses': 60,
                'avatar': new_avatar_url
            }
        }
        res_update = self.app.post('/api/client/update', data=json.dumps(update_payload), content_type='application/json')
        self.assertEqual(res_update.status_code, 200)
        self.assertTrue(json.loads(res_update.data)['success'])

        # 5. Verificar que el perfil y el nuevo avatar quedaron persistidos en SQLite
        res_verify = self.app.get(f'/api/client/{client_id}')
        updated_client = json.loads(res_verify.data)['client']
        self.assertEqual(updated_client['nombre'], 'Cliente Con Foto Actualizada')
        self.assertEqual(updated_client['ocupacion'], 'CTO & VP Engineering')
        self.assertEqual(updated_client['avatar'], new_avatar_url)

        # 6. Limpieza
        self.app.post('/api/client/delete', data=json.dumps({'client_id': client_id}), content_type='application/json')


if __name__ == '__main__':
    unittest.main()
