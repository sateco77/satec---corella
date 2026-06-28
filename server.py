#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA Multiperfil para SATEC NETWORK
Unificado: Chat + Procesamiento de correos + Asignación de tareas + Heartbeat
"""

import os
import json
import requests
import imaplib
import smtplib
import email
import ssl
import threading
import time
import logging
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# CONFIGURACIÓN DE CORREO
# ============================================================

EMAIL_USER = os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')

# IDs de agentes en la base de datos (IDs REALES)
AGENTE_AGATA_ID = 53
AGENTE_LUCIA_ID = 54
AGENTE_ORION_ID = 55

# ============================================================
# PERFILES DE AGENTES
# ============================================================

PERFILES = {
    "agata": {
        "id": "agata",
        "nombre": "Ágata",
        "rol": "Ventas y Marketing",
        "emoji": "📊"
    },
    "lucia": {
        "id": "lucia",
        "nombre": "Lucía",
        "rol": "Atención al Cliente",
        "emoji": "💬"
    },
    "orion": {
        "id": "orion",
        "nombre": "Orion",
        "rol": "Soporte Técnico",
        "emoji": "🔧"
    }
}

# ============================================================
# HEARTBEAT AL CRM
# ============================================================

def enviar_heartbeat():
    """Envía señal de vida al CRM cada 30 segundos"""
    crm_url = "https://satecnetwork.com/crm/api_crm.php"
    while True:
        try:
            response = requests.post(
                f"{crm_url}?path=agente_heartbeat",
                json={
                    'agente_id': 'corella_server',
                    'perfiles': list(PERFILES.keys()),
                    'estado': 'online',
                    'timestamp': datetime.now().isoformat()
                },
                timeout=10
            )
            if response.status_code == 200:
                print("💓 Heartbeat enviado")
            else:
                print(f"⚠️ Heartbeat: {response.status_code}")
        except Exception as e:
            print(f"❌ Heartbeat falló: {e}")
        time.sleep(30)

# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route('/')
def index():
    return jsonify({
        'service': 'CORELLA SATEC',
        'status': 'online',
        'version': '3.0',
        'perfiles': list(PERFILES.keys()),
        'soporte': '+52 938 120 6643'
    })

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC',
        'version': '3.0',
        'perfiles': list(PERFILES.keys()),
        'soporte': '+52 938 120 6643'
    })

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('mensaje') or data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje'}), 400
        
        return jsonify({
            'response': f"🤖 Mensaje recibido: '{user_message}'. Soy CORELLA, el asistente multiperfil.",
            'perfil': 'lucia',
            'agente': 'Lucía',
            'rol': 'Atención al Cliente',
            'emoji': '💬'
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/test-correo')
def test_correo():
    return jsonify({"status": "✅ Servidor Corella corriendo correctamente", "heartbeat": "activo"})

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA Multiperfil")
    print("=" * 60)
    for key, data in PERFILES.items():
        print(f"   {data['emoji']} {data['nombre']} ({data['rol']})")
    print("=" * 60)
    print(f"📧 Correo: {EMAIL_USER}")
    print(f"🌐 Puerto: {PORT}")
    print("=" * 60)
    print("💓 Heartbeat iniciado (cada 30 segundos)")
    print("=" * 60)
    
    # Iniciar heartbeat en hilo separado
    threading.Thread(target=enviar_heartbeat, daemon=True).start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
