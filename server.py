#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA Multiperfil con LECTOR DE MÚLTIPLES CORREOS
- contacto@satecnetwork.com -> ORION (Soporte)
- ventas@satecnetwork.com -> LUCÍA (Ventas)
"""

import os
import requests
import imaplib
import smtplib
import email
import ssl
import threading
import time
import logging
from email.mime.text import MIMEText
from flask import Flask, request, jsonify
from flask_cors import CORS
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__)
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# CONFIGURACIÓN DE CORREOS (desde variables de entorno)
# ============================================================

# Correo CONTACTO (Orion - Soporte)
EMAIL_CONTACTO = os.environ.get('EMAIL_USER_CONTACTO', 'contacto@satecnetwork.com')
PASS_CONTACTO = os.environ.get('EMAIL_PASS_CONTACTO', '')
AGENTE_ORION_ID = 55

# Correo VENTAS (Lucía - Ventas)
EMAIL_VENTAS = os.environ.get('EMAIL_USER_VENTAS', 'ventas@satecnetwork.com')
PASS_VENTAS = os.environ.get('EMAIL_PASS_VENTAS', '')
AGENTE_LUCIA_ID = 54

# Configuración IMAP/SMTP
IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')

# URL del CRM
CRM_API_URL = os.environ.get('CRM_API_URL', 'https://satecnetwork.com/crm/api_crm.php')

# ============================================================
# PERFILES
# ============================================================

PERFILES = {
    "orion": {
        "id": "orion",
        "nombre": "Orion",
        "rol": "Soporte Técnico",
        "emoji": "🔧",
        "email": EMAIL_CONTACTO,
        "agente_id": AGENTE_ORION_ID
    },
    "lucia": {
        "id": "lucia",
        "nombre": "Lucía",
        "rol": "Ventas",
        "emoji": "💬",
        "email": EMAIL_VENTAS,
        "agente_id": AGENTE_LUCIA_ID
    }
}

# ============================================================
# FUNCIONES DE CORREO
# ============================================================

def conectar_imap(email_user, email_password):
    """Conecta al servidor IMAP"""
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(email_user, email_password)
        mail.select('INBOX')
        return mail
    except Exception as e:
        print(f"❌ Error IMAP para {email_user}: {e}")
        return None

def crear_tarea_en_crm(remitente, asunto, cuerpo, agente_id):
    """Crea una tarea en el CRM vía API"""
    try:
        payload = {
            'texto': f"Correo de {remitente}: {asunto[:50]}...",
            'fecha_limite': datetime.now().strftime('%Y-%m-%d'),
            'asignada_a': agente_id,
            'asignada_por': 1,
            'fuente': 'correo'
        }
        
        response = requests.post(
            f"{CRM_API_URL}?path=tareas",
            json=payload,
            timeout=15
        )
        
        if response.status_code == 200:
            return True
        else:
            print(f"⚠️ Error API: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Error API: {e}")
        return False

def procesar_correos(email_user, email_password, agente_id, nombre_agente):
    """Procesa correos de una cuenta específica"""
    if not email_password:
        print(f"⚠️ Sin contraseña para {email_user}")
        return
    
    mail = conectar_imap(email_user, email_password)
    if not mail:
        return
    
    try:
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
                
                if crear_tarea_en_crm(remitente, asunto, cuerpo, agente_id):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    print(f"✅ Correo procesado y marcado como leído")
                else:
                    print(f"⚠️ No se pudo crear la tarea")
                
            except Exception as e:
                print(f"❌ Error procesando correo: {e}")
                continue
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        print(f"❌ Error general: {e}")

def procesar_todos_los_correos():
    """Procesa correos de todas las cuentas"""
    print("📬 Procesando todas las cuentas...")
    
    # Procesar Orion (contacto)
    procesar_correos(
        EMAIL_CONTACTO,
        PASS_CONTACTO,
        AGENTE_ORION_ID,
        "Orion"
    )
    
    # Procesar Lucía (ventas)
    procesar_correos(
        EMAIL_VENTAS,
        PASS_VENTAS,
        AGENTE_LUCIA_ID,
        "Lucía"
    )
    
    print("📬 Procesamiento completado")

# ============================================================
# TAREAS PROGRAMADAS
# ============================================================

def revisar_correos_periodicamente():
    """Revisa correos cada 30 segundos"""
    while True:
        try:
            procesar_todos_los_correos()
        except Exception as e:
            print(f"❌ Error: {e}")
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
        'perfiles': list(PERFILES.keys())
    })

@app.route('/test-correo', methods=['GET'])
def test_correo():
    """Endpoint para probar manualmente"""
    print("🧪 TEST-CORREO EJECUTADO")
    procesar_todos_los_correos()
    return jsonify({
        "status": "Correos procesados",
        "timestamp": datetime.now().isoformat(),
        "cuentas": [PERFILES['orion']['email'], PERFILES['lucia']['email']]
    })

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Lector de Múltiples Correos")
    print("=" * 60)
    print(f"📧 Orion (Soporte): {EMAIL_CONTACTO}")
    print(f"📧 Lucía (Ventas): {EMAIL_VENTAS}")
    print("=" * 60)
    print(f"🌐 Puerto: {PORT}")
    print("📬 Lector de correos activo (cada 30 segundos)")
    print("=" * 60)
    
    # Iniciar lector de correos en hilo separado
    threading.Thread(target=revisar_correos_periodicamente, daemon=True).start()
    
    app.run(host='0.0.0.0', port=PORT, debug=False)
