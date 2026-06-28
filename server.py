#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA Multiperfil con LECTOR DE CORREOS
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

# IDs de agentes en la base de datos
AGENTE_AGATA_ID = 53
AGENTE_LUCIA_ID = 54
AGENTE_ORION_ID = 55

# URL del CRM
CRM_API_URL = "https://satecnetwork.com/crm/api_crm.php"

PERFILES = {
    "agata": {"id": "agata", "nombre": "Ágata", "rol": "Ventas y Marketing", "emoji": "📊"},
    "lucia": {"id": "lucia", "nombre": "Lucía", "rol": "Atención al Cliente", "emoji": "💬"},
    "orion": {"id": "orion", "nombre": "Orion", "rol": "Soporte Técnico", "emoji": "🔧"}
}

# ============================================================
# FUNCIONES DE CORREO
# ============================================================

def conectar_imap():
    """Conecta al servidor IMAP"""
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(EMAIL_USER, EMAIL_PASSWORD)
        mail.select('INBOX')
        return mail
    except Exception as e:
        print(f"❌ Error IMAP: {e}")
        return None

def crear_tarea_en_crm(remitente, asunto, cuerpo, agente_id=54):
    """Crea una tarea en el CRM vía API"""
    try:
        params = {'path': 'tareas'}
        payload = {
            'texto': f"Correo de {remitente}: {asunto[:50]}...",
            'fecha_limite': datetime.now().strftime('%Y-%m-%d'),
            'asignada_a': agente_id,
            'asignada_por': 1,
            'fuente': 'correo'
        }
        
        response = requests.post(CRM_API_URL, params=params, json=payload, timeout=15)
        if response.status_code == 200:
            print(f"✅ Tarea creada para agente ID {agente_id}")
            return True
        else:
            print(f"⚠️ Error creando tarea: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error API: {e}")
        return False

def detectar_agente_por_correo(asunto, cuerpo):
    """Detecta qué agente debe atender el correo"""
    texto = (asunto + " " + cuerpo).lower()
    
    if "soporte" in texto or "problema" in texto or "falla" in texto:
        return AGENTE_ORION_ID  # 55
    elif "ventas" in texto or "cotización" in texto or "precio" in texto:
        return AGENTE_AGATA_ID  # 53
    else:
        return AGENTE_LUCIA_ID  # 54 (por defecto)

def procesar_correos():
    """Lee correos no leídos y crea tareas"""
    mail = conectar_imap()
    if not mail:
        return
    
    try:
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        
        if not email_ids:
            print("📭 No hay correos nuevos")
            mail.close()
            mail.logout()
            return
        
        print(f"📧 {len(email_ids)} correos nuevos")
        
        for email_id in email_ids:
            try:
                result, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                remitente = msg.get('From', 'Desconocido')
                asunto = msg.get('Subject', 'Sin asunto')
                cuerpo = ""
                
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            cuerpo = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    cuerpo = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                print(f"📥 De: {remitente} | Asunto: {asunto[:50]}")
                
                agente_id = detectar_agente_por_correo(asunto, cuerpo)
                
                if crear_tarea_en_crm(remitente, asunto, cuerpo, agente_id):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    print(f"✅ Correo procesado y marcado como leído")
                
            except Exception as e:
                print(f"❌ Error procesando correo: {e}")
                continue
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"❌ Error general: {e}")

# ============================================================
# HEARTBEAT AL CRM
# ============================================================

def enviar_heartbeat():
    """Envía señal de vida al CRM cada 30 segundos"""
    while True:
        try:
            response = requests.post(
                f"{CRM_API_URL}?path=agente_heartbeat",
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

def revisar_correos_periodicamente():
    """Revisa correos cada 30 segundos"""
    while True:
        try:
            procesar_correos()
        except Exception as e:
            print(f"❌ Error en lector de correos: {e}")
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

@app.route('/test-correo')
def test_correo():
    """Endpoint para probar la lectura de correos"""
    procesar_correos()
    return jsonify({"status": "Correos procesados", "timestamp": datetime.now().isoformat()})

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

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA con Lector de Correos")
    print("=" * 60)
    for key, data in PERFILES.items():
        print(f"   {data['emoji']} {data['nombre']} ({data['rol']})")
    print("=" * 60)
    print(f"📧 Correo: {EMAIL_USER}")
    print(f"🌐 Puerto: {PORT}")
    print("=" * 60)
    print("💓 Heartbeat iniciado (cada 30 segundos)")
    print("📬 Lector de correos iniciado (cada 30 segundos)")
    print("=" * 60)
    
    # Iniciar heartbeat en hilo separado
    threading.Thread(target=enviar_heartbeat, daemon=True).start()
    
    # Iniciar lector de correos en hilo separado
    threading.Thread(target=revisar_correos_periodicamente, daemon=True).start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
