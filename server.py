#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import logging
import requests
import imaplib
import email
import ssl
from datetime import datetime
from flask import Flask, jsonify

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = Flask(__name__)

EMAIL_VENTAS = os.environ.get('EMAIL_VENTAS', 'ventas@satecnetwork.com')
EMAIL_VENTAS_PASSWORD = os.environ.get('PASSWORD_VENTAS', '')
IMAP_SERVER = 'imap.hostinger.com'
API_URL = "https://satecnetwork.com/crm/api_crm.php"

def crear_tarea_en_hostinger(remitente, asunto):
    try:
        params = {'path': 'tarea_agente'}
        payload = {
            'texto': f"Correo de {remitente}: {asunto[:50]}",
            'fecha_limite': datetime.now().strftime('%Y-%m-%d'),
            'asignada_a': 54, 
            'asignada_por': 1,
            'fuente': 'correo'
        }
        
        logger.info(f"📤 Enviando POST con params {params}")
        response = requests.post(API_URL, params=params, json=payload, timeout=15)
        logger.info(f"📡 Estado HTTP: {response.status_code} | Respuesta: {response.text}")
        return True
    except Exception as e:
        logger.error(f"❌ Error API: {e}")
        return False

def revisar_correos_prueba():
    if not EMAIL_VENTAS_PASSWORD:
        logger.warning("⚠️ Sin PASSWORD_VENTAS configurado.")
        return
        
    try:
        logger.info("📡 Conectando a IMAP...")
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=ssl.create_default_context())
        mail.login(EMAIL_VENTAS, EMAIL_VENTAS_PASSWORD)
        mail.select('INBOX')
        
        _, data = mail.search(None, 'ALL')
        ids = data[0].split()
        
        if ids:
            _, msg_data = mail.fetch(ids[-1], '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            crear_tarea_en_hostinger(msg.get('From', 'Desconocido'), msg.get('Subject', 'Sin Asunto'))
        else:
            logger.info("📭 Bandeja vacía.")
            
        mail.close()
        mail.logout()
    except Exception as e:
        logger.error(f"❌ Error IMAP: {e}")

@app.route('/test-correo')

def enviar_heartbeat():
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

threading.Thread(target=enviar_heartbeat, daemon=True).start()


def test_correo():
    revisar_correos_prueba()
    return jsonify({"status": "Prueba ejecutada, revisa los logs"})

@app.route('/')
def health():
    return jsonify({"status": "Bot Minimo Corriendo"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)))
