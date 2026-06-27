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
# CONFIGURACIÓN DE LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# CONFIGURACIÓN DE CORREO (MÚLTIPLES CUENTAS)
# ============================================================

# Cuenta 1: ORION (Soporte - contacto@satecnetwork.com)
EMAIL_USER = os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# Cuenta 2: LUCÍA (Ventas - ventas@satecnetwork.com)
EMAIL_VENTAS = os.environ.get('EMAIL_VENTAS', 'ventas@satecnetwork.com')
EMAIL_VENTAS_PASSWORD = os.environ.get('PASSWORD_VENTAS', '')

# Cuenta 3: ÁGATA (Marketing - agata@satecnetwork.com) - Opcional
EMAIL_AGATA = os.environ.get('EMAIL_AGATA', 'agata@satecnetwork.com')
EMAIL_AGATA_PASSWORD = os.environ.get('PASSWORD_AGATA', '')

IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')

# ============================================================
# CONFIGURACIÓN DE BASE DE DATOS
# ============================================================

DB_HOST = os.environ.get('DB_HOST', 'peru-clam-144838.hostingersite.com')
DB_USER = os.environ.get('DB_USER', 'u416165369_corella75')
DB_PASSWORD = os.environ.get('DB_PASSWORD', '7Crm7408')
DB_NAME = os.environ.get('DB_NAME', 'u416165369_corella_crm')

# ============================================================
# IDs DE AGENTES EN LA BASE DE DATOS
# ============================================================

AGENTE_AGATA_ID = int(os.environ.get('AGENTE_AGATA_ID', 53))
AGENTE_LUCIA_ID = int(os.environ.get('AGENTE_LUCIA_ID', 54))
AGENTE_ORION_ID = int(os.environ.get('AGENTE_ORION_ID', 55))

# ============================================================
# ESPECIALIDADES Y AGENTES (CORREGIDO)
# ============================================================

ESPECIALIDADES = {
    'gps': {
        'palabras': ['gps', 'rastreo', 'flota', 'geocerca', 'corte motor', 'localización', 'vehículo', 'tracking'],
        'agente_id': AGENTE_AGATA_ID,
        'nombre': 'Ágata (IA)',
        'perfil': 'agata',
        'emoji': '📊'
    },
    'cctv': {
        'palabras': ['cámara', 'video', 'vigilancia', 'cctv', 'movimiento', 'perimetral', 'grabación', 'ia', 'reconocimiento'],
        'agente_id': AGENTE_LUCIA_ID,
        'nombre': 'Lucía (IA)',
        'perfil': 'lucia',
        'emoji': '💬'
    },
    'access': {
        'palabras': ['acceso', 'biometría', 'huella', 'qr', 'tarjeta', 'lector', 'control acceso', 'credencial'],
        'agente_id': AGENTE_LUCIA_ID,
        'nombre': 'Lucía (IA)',
        'perfil': 'lucia',
        'emoji': '💬'
    },
    'chip_taxi': {
        'palabras': ['taxi', 'viaje', 'app', 'conductor', 'chip taxi', 'pasajero', 'solicitar viaje', 'tarifa'],
        'agente_id': AGENTE_AGATA_ID,
        'nombre': 'Ágata (IA)',
        'perfil': 'agata',
        'emoji': '📊'
    },
    'soporte': {
        'palabras': ['falla', 'error', 'problema', 'no funciona', 'instalar', 'configurar', 'técnico', 'ayuda'],
        'agente_id': AGENTE_ORION_ID,
        'nombre': 'Orion (IA)',
        'perfil': 'orion',
        'emoji': '🔧'
    }
}

PERFILES = {
    'agata': {
        'nombre': 'Ágata',
        'rol': 'Ventas y Marketing',
        'emoji': '📊',
        'prompt': 'Eres ÁGATA, experta en Ventas y Marketing de SATEC. Tono persuasivo y entusiasta.'
    },
    'lucia': {
        'nombre': 'Lucía',
        'rol': 'Atención al Cliente',
        'emoji': '💬',
        'prompt': 'Eres LUCÍA, experta en Atención al Cliente de SATEC. Tono cálido y empático.'
    },
    'orion': {
        'nombre': 'Orion',
        'rol': 'Soporte Técnico',
        'emoji': '🔧',
        'prompt': 'Eres ORION, experto en Soporte Técnico de SATEC. Tono técnico pero claro.'
    }
}

FALLBACK_RESPUESTAS = {
    'agata': "📊 ¡Gracias por contactar a SATEC! Soy Ágata, tu asesora de ventas. 🚀",
    'lucia': "💬 Soy Lucía, tu asesora de atención al cliente. ¿En qué puedo ayudarte? ❤️",
    'orion': "🔧 Soy Orion, tu técnico de soporte. ¿Puedes darme más detalles? 💻"
}

# ============================================================
# DETECCIÓN DE ESPECIALIDAD
# ============================================================

def detectar_especialidad(texto):
    """Detecta la especialidad basada en palabras clave"""
    texto_lower = texto.lower()
    for esp, data in ESPECIALIDADES.items():
        for palabra in data['palabras']:
            if palabra in texto_lower:
                logger.info(f"🔍 Especialidad detectada: {esp} (palabra: '{palabra}')")
                return esp
    logger.info("⚠️ No se detectó especialidad")
    return None

def detectar_perfil(user_message, perfil_especifico=None):
    """Detecta el perfil del agente"""
    if perfil_especifico and perfil_especifico in PERFILES:
        return perfil_especifico
    
    texto = user_message.lower()
    
    for perfil_id, data in PERFILES.items():
        for palabra in data.get('palabras_clave', []):
            if palabra in texto:
                return perfil_id
    
    # Si no se detecta perfil, usar especialidad
    especialidad = detectar_especialidad(user_message)
    if especialidad and especialidad in ESPECIALIDADES:
        return ESPECIALIDADES[especialidad]['perfil']
    
    return "lucia"

# ============================================================
# FUNCIONES DE CORREO
# ============================================================

def conectar_imap(email_user, email_password):
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(email_user, email_password)
        mail.select('INBOX')
        return mail
    except Exception as e:
        logger.error(f"❌ Error IMAP para {email_user}: {e}")
        return None

def enviar_correo(para, asunto, mensaje, email_user, email_password):
    try:
        msg = MIMEText(mensaje, 'plain', 'utf-8')
        msg['Subject'] = asunto
        msg['From'] = email_user
        msg['To'] = para
        
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context)
        server.login(email_user, email_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Correo enviado a {para}")
        return True
    except Exception as e:
        logger.error(f"❌ Error SMTP: {e}")
        return False

# ============================================================
# FUNCIÓN PARA CREAR TAREA VÍA API DE HOSTINGER
# ============================================================

def crear_tarea_en_bd(remitente, asunto, agente_id):
    """Crea una tarea usando la API de Hostinger con CSRF token"""
    try:
        api_url = "https://peru-clam-144838.hostingersite.com/crm/api_crm.php"
        
        # 1. Obtener token CSRF
        logger.info("🔑 Obteniendo token CSRF...")
        token_response = requests.get(
            f"{api_url}?path=csrf_token",
            timeout=10
        )
        
        if token_response.status_code != 200:
            logger.error(f"❌ Error obteniendo CSRF: {token_response.status_code}")
            return False
            
        token_data = token_response.json()
        csrf_token = token_data.get('csrf_token')
        
        if not csrf_token:
            logger.error("❌ No se recibió CSRF token")
            return False
            
        logger.info("✅ CSRF token obtenido")
        
        # 2. Crear tarea con el token
        texto_tarea = f"Correo de {remitente}: {asunto[:50]}..."
        
        response = requests.post(
            f"{api_url}?path=tareas",
            json={
                'texto': texto_tarea,
                'fecha_limite': datetime.now().strftime('%Y-%m-%d'),
                'asignada_a': agente_id,
                'asignada_por': 1,
                'fuente': 'correo',
                'csrf_token': csrf_token  # ← Agregar el token aquí
            },
            timeout=30,
            headers={'Content-Type': 'application/json'}
        )
        
        if response.status_code == 200:
            data = response.json()
            if data.get('success'):
                logger.info(f"✅ Tarea creada para agente {agente_id} (ID: {data.get('id', 'N/A')})")
                return True
            else:
                logger.error(f"❌ Error API: {data.get('error')}")
        else:
            logger.error(f"❌ API respondió con {response.status_code}: {response.text}")
            
    except Exception as e:
        logger.error(f"❌ Error creando tarea: {e}")
    
    return False


def generar_respuesta(user_message, perfil):
    """Genera respuesta usando respuestas predefinidas (fallback)"""
    perfil_data = PERFILES.get(perfil, PERFILES["lucia"])
    
    # Respuestas predefinidas según el perfil
    respuestas = {
        'agata': f"📊 ¡Hola! Soy Ágata, tu asesora de ventas. He recibido tu mensaje y lo he derivado al área correspondiente. Un asesor se pondrá en contacto contigo en las próximas 24 horas. ¡Gracias por contactar a SATEC! 🚀",
        'lucia': f"💬 ¡Hola! Soy Lucía, tu asesora de atención al cliente. Tu consulta ha sido registrada y un especialista te responderá a la brevedad. ¿Necesitas algo más? ❤️",
        'orion': f"🔧 ¡Hola! Soy Orion, tu técnico de soporte. He recibido tu reporte y ya está siendo analizado por nuestro equipo. Te notificaremos cuando tengamos una solución. 💻"
    }
    
    return respuestas.get(perfil, FALLBACK_RESPUESTAS.get(perfil, "Hemos recibido tu mensaje. Un asesor te contactará pronto."))

def procesar_correo_individual(mail, email_id, nombre_cuenta):
    """Procesa un correo individual y asigna tarea"""
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
        
        logger.info(f"📧 De: {remitente} | Asunto: {asunto}")
        
        texto_completo = f"{asunto}\n{cuerpo}"
        especialidad = detectar_especialidad(texto_completo)
        
        # Si no detecta especialidad, asignar según la cuenta
        if not especialidad:
            if nombre_cuenta == 'Orion' or 'contacto' in nombre_cuenta.lower():
                especialidad = 'soporte'
            elif nombre_cuenta == 'Ágata' or 'agata' in nombre_cuenta.lower():
                especialidad = 'gps'
            else:
                especialidad = 'cctv'
        
        if especialidad and especialidad in ESPECIALIDADES:
            agente = ESPECIALIDADES[especialidad]
            logger.info(f"✅ Asignando a {agente['nombre']} (ID: {agente['agente_id']})")
            
            # Crear tarea en la BD (con CSRF)
            tarea_creada = crear_tarea_en_bd(remitente, asunto, agente['agente_id'])
            
            if tarea_creada:
                # Enviar respuesta de confirmación (sin Ollama)
                perfil = agente['perfil']
                respuesta = generar_respuesta_simple(perfil)
                
                # Obtener la cuenta de correo correcta
                if perfil == 'orion':
                    email_from = EMAIL_USER
                    password_from = EMAIL_PASSWORD
                elif perfil == 'agata':
                    email_from = EMAIL_AGATA if EMAIL_AGATA else EMAIL_USER
                    password_from = EMAIL_AGATA_PASSWORD if EMAIL_AGATA_PASSWORD else EMAIL_PASSWORD
                else:
                    email_from = EMAIL_VENTAS
                    password_from = EMAIL_VENTAS_PASSWORD
                
                if enviar_correo(remitente, f"Re: {asunto}", respuesta, email_from, password_from):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    logger.info(f"✉️ Respuesta enviada a {remitente} desde {email_from}")
                else:
                    logger.warning(f"⚠️ No se pudo enviar respuesta a {remitente}")
            else:
                logger.error(f"❌ No se pudo crear la tarea para {remitente}")
        else:
            logger.warning("⚠️ No se pudo clasificar el correo")
            
    except Exception as e:
        logger.error(f"❌ Error procesando correo: {e}")


def leer_correos():
    """Lee correos no leídos de ambas cuentas"""
    cuentas = [
        {'email': EMAIL_USER, 'password': EMAIL_PASSWORD, 'nombre': 'Orion'},
        {'email': EMAIL_VENTAS, 'password': EMAIL_VENTAS_PASSWORD, 'nombre': 'Lucía'},
        {'email': EMAIL_AGATA, 'password': EMAIL_AGATA_PASSWORD, 'nombre': 'Ágata'}
    ]
    
    for cuenta in cuentas:
        if not cuenta['email'] or not cuenta['password']:
            continue
            
        logger.info(f"📡 Revisando cuenta: {cuenta['email']}")
        try:
            mail = conectar_imap(cuenta['email'], cuenta['password'])
            if not mail:
                continue
            
            result, data = mail.search(None, 'UNSEEN')
            correos_ids = data[0].split()
            
            logger.info(f"📧 {cuenta['email']}: {len(correos_ids)} correos no leídos")
            
            for email_id in correos_ids:
                procesar_correo_individual(mail, email_id, cuenta['nombre'])
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"❌ Error en cuenta {cuenta['email']}: {e}")

def procesar_correos():
    """Wrapper para procesar correos desde el endpoint"""
    logger.info("📬 Procesando correos...")
    leer_correos()
    return {'success': True, 'message': 'Correos procesados'}

# ============================================================
# HEARTBEAT AL CRM
# ============================================================

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
                logger.info("💓 Heartbeat enviado")
            else:
                logger.warning(f"⚠️ Heartbeat falló: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Heartbeat falló: {e}")
        time.sleep(30)

# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('web', path)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('mensaje') or data.get('message', '')
        perfil_especifico = data.get('perfil', 'auto')
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje'}), 400
        
        perfil = detectar_perfil(user_message, perfil_especifico)
        respuesta = generar_respuesta(user_message, perfil)
        
        return jsonify({
            'response': respuesta,
            'perfil': perfil,
            'agente': PERFILES[perfil]['nombre'],
            'rol': PERFILES[perfil]['rol'],
            'emoji': PERFILES[perfil]['emoji']
        })
    
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/procesar_correos', methods=['GET', 'POST'])
def procesar_correos_endpoint():
    resultado = procesar_correos()
    return jsonify({
        'success': True,
        'message': 'Correos procesados',
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/perfiles', methods=['GET'])
def get_perfiles():
    perfiles = []
    for key, data in PERFILES.items():
        perfiles.append({
            'id': key,
            'nombre': data['nombre'],
            'rol': data['rol'],
            'emoji': data['emoji']
        })
    return jsonify({'perfiles': perfiles})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC',
        'version': '3.0',
        'perfiles': list(PERFILES.keys()),
        'soporte': '+52 938 120 6643'
    })

# ============================================================
# SCHEDULER: REVISAR CORREOS CADA 60 SEGUNDOS
# ============================================================

def scheduler_loop():
    """Ejecuta procesar_correos() cada 60 segundos en segundo plano"""
    while True:
        try:
            logger.info("📬 Revisando correos...")
            leer_correos()
        except Exception as e:
            logger.error(f"❌ Error en scheduler: {e}")
        time.sleep(60)

# ============================================================
# INICIAR HILOS EN SEGUNDO PLANO
# ============================================================

# Iniciar heartbeat
threading.Thread(target=enviar_heartbeat, daemon=True).start()
logger.info("🔄 Heartbeat thread iniciado")

# Iniciar scheduler de correos
threading.Thread(target=scheduler_loop, daemon=True).start()
logger.info("🔄 Scheduler de correos iniciado (cada 60 segundos)")

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA Multiperfil")
    print("=" * 60)
    print("📊 Ágata (Ventas y Marketing)")
    print("💬 Lucía (Atención al Cliente)")
    print("🔧 Orion (Soporte Técnico)")
    print("=" * 60)
    print(f"📧 Correo Orion: {EMAIL_USER}")
    print(f"📧 Correo Lucía: {EMAIL_VENTAS}")
    print(f"📧 Correo Ágata: {EMAIL_AGATA}")
    print(f"🌐 Puerto: {PORT}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
