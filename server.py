#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import time
import logging
import requests
import imaplib
import email
import ssl
from datetime import datetime
from flask import Flask, jsonify

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# CONFIGURACIÓN CRUCIAL (Revisa que coincida con tus credenciales de Hostinger)
EMAIL_VENTAS = os.environ.get('EMAIL_VENTAS', 'ventas@satecnetwork.com')
EMAIL_VENTAS_PASSWORD = os.environ.get('PASSWORD_VENTAS', '')
IMAP_SERVER = 'imap.hostinger.com'

# URL Limpia sin barras diagonales al final
API_URL = "https://satecnetwork.com/crm/api_crm.php"

def crear_tarea_en_hostinger(remitente, asunto):
    try:
        # Enviamos 'action' como parámetro URL (?action=tarea_agente)
        params = {'action': 'tarea_agente'}
        
        payload = {
            'texto': f"Correo de {remitente}: {asunto[:50]}",
            'fecha_limite': datetime.now().strftime('%Y-%m-%d'),
            'asignada_a': 54, # ID Fijo de Lucía para la prueba
            'asignada_por': 1,
            'fuente': 'correo'
        }
        
        logger.info(f"📤 Enviando POST a: {API_URL} con params {params}")
        
        response = requests.post(
            API_URL,
            params=params,
            json=payload,
            timeout=15,
            headers={'Content-Type': 'application/json', 'Accept': 'application/json'}
        )
        
        logger.info(f"📡 Estado HTTP: {response.status_code}")
        logger.info(f"📡 Respuesta del Servidor: {response.text}")
        return True
    except Exception as e:
        logger.error(f"❌ Error en la petición: {e}")
        return False

def revisar_correos_prueba():
    if not EMAIL_VENTAS_PASSWORD:
        logger.warning("⚠️ No hay contraseña configurada para el correo.")
        return
        
    try:
        logger.info(f"📡 Conectando a {EMAIL_VENTAS}...")
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(EMAIL_VENTAS, EMAIL_VENTAS_PASSWORD)
        mail.select('INBOX')
        
        # Buscamos el último correo de la bandeja
        result, data = mail.search(None, 'ALL')
        ids = data[0].split()
        
        if len(ids) > 0:
            ultimo_id = ids[-1]
            res, msg_data = mail.fetch(ultimo_id, '(RFC822)')
            msg = email.message_from_bytes(msg_data[0][1])
            
            remitente = msg.get('From', 'Desconocido')
            asunto = msg.get('Subject', 'Sin Asunto')
            
            logger.info(f"📧 Último correo detectado -> De: {remitente} | Asunto: {asunto}")
            crear_tarea_en_hostinger(remitente, asunto)
        else:
            logger.info("📭 No se encontraron correos en la bandeja.")
            
        mail.close()
        mail.logout()
    except Exception as e:
        logger.error(f"❌ Error leyendo buzón: {e}")

# Endpoint simple para gatillar la prueba manualmente desde el navegador/Render
@app.route('/test-correo')
def test_correo():
    revisar_correos_prueba()
    return jsonify({"status": "Prueba ejecutada, revisa los logs de Render"})

@app.route('/')
def health():
    return jsonify({"status": "Bot Minimo Corriendo"})

if __name__ == '__main__':
    PORT = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=PORT)
