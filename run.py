"""
Script de arranque para el Módulo de Evaluación y Consulta Crediticia (CreditSense).
Abre automáticamente el navegador y ejecuta la aplicación Flask.
"""

import sys
import os
import time
import webbrowser
import threading

# Asegurar path correcto
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
if CURRENT_DIR not in sys.path:
    sys.path.insert(0, CURRENT_DIR)

from app import app

def open_browser():
    """Espera un segundo a que el servidor levante y abre el navegador."""
    time.sleep(1.2)
    url = "http://127.0.0.1:5000"
    print(f"\n[+] Abriendo CreditSense en tu navegador: {url}")
    webbrowser.open(url)

if __name__ == '__main__':
    print("=" * 72)
    print("  CREDITSENSE - MODULO DE EVALUACION CREDITICIA BANCARIA")
    print("  Analizador de Comportamiento Financiero (Ultimos 6 Meses)")
    print("=" * 72)
    print("  -> Servidor Web iniciado en: http://127.0.0.1:5000")
    print("  -> Presiona Ctrl+C en esta consola para detener el servidor.")
    print("=" * 72)
    
    # Iniciar hilo para abrir navegador
    threading.Thread(target=open_browser, daemon=True).start()
    
    # Ejecutar Flask
    app.run(host='127.0.0.1', port=5000, debug=False)
