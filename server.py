#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA Multiperfil con LECTOR DE MÚLTIPLES CORREOS
- contacto@satecnetwork.com -> ORION (Soporte, ID 55)
- ventas@satecnetwork.com -> LUCÍA (Ventas, ID 54)
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
# CONFIGURACIÓN DE MÚLTIPLES CORREOS
# ============================================================

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

# Configuración de cuentas de correo
CUENTAS_CORREO = [
    {
        "email": os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com'),
        "password": os.environ.get('EMAIL_PASSWORD', ''),
        "agente_id": AGENTE_ORION_ID,  # Orion
        "nombre_agente": "Orion",
        "imap_server": "imap.hostinger.com",
        "smtp_server": "smtp.hostinger.com",
        "descripcion": "Soporte Técnico"
    },
    {
        "email": os.environ.get('EMAIL_VENTAS', 'ventas@satecnetwork.com'),
        "password": os.environ.get('PASSWORD_VENTAS', ''),
        "agente_id": AGENTE_LUCIA_ID,  # Lucía
        "nombre_agente": "Lucía",
        "imap_server": "imap.hostinger.com",
        "smtp_server": "smtp.hostinger.com",
        "descripcion": "Ventas"
    }
]

# Mostrar configuración al iniciar
print("📧 CUENTAS DE CORREO CONFIGURADAS:")
for cuenta in CUENTAS_CORREO:
    print(f"   - {cuenta['email']} → {cuenta['nombre_agente']} (ID: {cuenta['agente_id']}) para {cuenta['descripcion']}")

# ============================================================
# FUNCIONES DE CORREO
# ============================================================

def conectar_imap(email_user, email_password, imap_server):
    """Conecta al servidor IMAP de una cuenta específica"""
    try:
        print(f"📡 Conectando a IMAP para {email_user}...")
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(imap_server, 993, ssl_context=context)
        print(f"🔐 Intentando login con {email_user}...")
        mail.login(email_user, email_password)
        mail.select('INBOX')
        print(f"✅ Conectado a {email_user}")
        return mail
    except imaplib.IMAP4.error as e:
        print(f"❌ Error IMAP para {email_user}: {e}")
        return None
    except Exception as e:
        print(f"❌ Error general para {email_user}: {e}")
        return None

def crear_tarea_en_crm(remitente, asunto, cuerpo, agente_id):
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
        
        print(f"📤 Creando tarea para agente {agente_id}...")
        response = requests.post(CRM_API_URL, params=params, json=payload, timeout=15)
        
        if response.status_code == 200:
            print(f"✅ Tarea creada para agente ID {agente_id}")
            return True
        else:
            print(f"⚠️ Error creando tarea: {response.status_code} - {response.text}")
            return False
    except Exception as e:
        print(f"❌ Error API: {e}")
        return False

def procesar_correos_cuenta(cuenta):
    """Lee correos no leídos de una cuenta específica y crea tareas"""
    email_user = cuenta['email']
    email_password = cuenta['password']
    agente_id = cuenta['agente_id']
    nombre_agente = cuenta['nombre_agente']
    imap_server = cuenta['imap_server']
    
    if not email_password:
        print(f"⚠️ Sin contraseña para {email_user}, omitiendo...")
        return
    
    mail = conectar_imap(email_user, email_password, imap_server)
    if not mail:
        return
    
    try:
        print(f"🔍 Buscando correos no leídos en {email_user}...")
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        
        if not email_ids:
            print(f"📭 No hay correos nuevos en {email_user}")
            mail.close()
            mail.logout()
            return
        
        print(f"📧 {len(email_ids)} correos nuevos en {email_user} para {nombre_agente}")
        
        for email_id in email_ids:
            try:
                print(f"📥 Procesando correo ID: {email_id} de {email_user}")
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
                
                print(f"📧 De: {remitente} | Asunto: {asunto[:50]}")
                
                if crear_tarea_en_crm(remitente, asunto, cuerpo, agente_id):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    print(f"✅ Correo de {email_user} procesado y marcado como leído")
                else:
                    print(f"⚠️ No se pudo crear la tarea para el correo de {email_user}")
                
            except Exception as e:
                print(f"❌ Error procesando correo ID {email_id} de {email_user}: {e}")
                continue
        
        mail.close()
        mail.logout()
        print(f"📬 Procesamiento de {email_user} completado")
        
    except Exception as e:
        print(f"❌ Error general en procesar_correos_cuenta para {email_user}: {e}")

def procesar_todos_los_correos():
    """Procesa correos de todas las cuentas configuradas"""
    print("📬 Iniciando procesamiento de todas las cuentas de correo...")
    for cuenta in CUENTAS_CORREO:
        procesar_correos_cuenta(cuenta)
    print("📬 Procesamiento de todas las cuentas completado")

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
    """Revisa correos de todas las cuentas cada 30 segundos"""
    while True:
        try:
            procesar_todos_los_correos()
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
    """Endpoint para probar la lectura de correos manualmente"""
    print("=" * 50)
    print("🧪 TEST-CORREO EJECUTADO MANUALMENTE")
    print("=" * 50)
    procesar_todos_los_correos()
    print("=" * 50)
    return jsonify({
        "status": "Correos procesados", 
        "timestamp": datetime.now().isoformat(),
        "cuentas": [c['email'] for c in CUENTAS_CORREO]
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

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA con Lector de Múltiples Correos")
    print("=" * 60)
    for key, data in PERFILES.items():
        print(f"   {data['emoji']} {data['nombre']} ({data['rol']})")
    print("=" * 60)
    print("📧 CUENTAS DE CORREO:")
    for cuenta in CUENTAS_CORREO:
        print(f"   - {cuenta['email']} → {cuenta['nombre_agente']} (ID: {cuenta['agente_id']})")
    print("=" * 60)
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
