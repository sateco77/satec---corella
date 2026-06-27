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
# CONFIGURACIÓN DE CORREO (MÚLTIPLES CUENTAS)
# ============================================================

# Cuenta 1: ORION (Soporte - contacto@satecnetwork.com)
EMAIL_USER = os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')

# Cuenta 2: LUCÍA (Ventas - ventas@satecnetwork.com)
EMAIL_VENTAS = os.environ.get('EMAIL_VENTAS', 'ventas@satecnetwork.com')
EMAIL_VENTAS_PASSWORD = os.environ.get('PASSWORD_VENTAS', '')

IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')



# IDs de agentes en la base de datos (IDs REALES de tu tabla)
AGENTE_AGATA_ID = int(os.environ.get('AGENTE_AGATA_ID', 53))
AGENTE_LUCIA_ID = int(os.environ.get('AGENTE_LUCIA_ID', 54))
AGENTE_ORION_ID = int(os.environ.get('AGENTE_ORION_ID', 55))

# ============================================================
# PERFILES DE AGENTES
# ============================================================

PERFILES = {
    'gps': {
        'palabras': ['gps', 'rastreo', 'flota', 'geocerca', 'corte motor', 'localización', 'vehículo', 'tracking'],
        'agente_id': 53,  # ← ÁGATA (ID REAL)
        'nombre': 'Ágata (IA)'
    },
    'cctv': {
        'palabras': ['cámara', 'video', 'vigilancia', 'cctv', 'movimiento', 'perimetral', 'grabación', 'ia', 'reconocimiento'],
        'agente_id': 54,  # ← LUCÍA (ID REAL)
        'nombre': 'Lucía (IA)'
    },
    'access': {
        'palabras': ['acceso', 'biometría', 'huella', 'qr', 'tarjeta', 'lector', 'control acceso', 'credencial'],
        'agente_id': 54,  # ← LUCÍA también (ID REAL)
        'nombre': 'Lucía (IA)'
    },
    'chip_taxi': {
        'palabras': ['taxi', 'viaje', 'app', 'conductor', 'chip taxi', 'pasajero', 'solicitar viaje', 'tarifa'],
        'agente_id': 53,  # ← ÁGATA (ID REAL)
        'nombre': 'Ágata (IA)'
    },
    'soporte': {
        'palabras': ['falla', 'error', 'problema', 'no funciona', 'instalar', 'configurar', 'técnico', 'ayuda'],
        'agente_id': 55,  # ← ORION (ID REAL)
        'nombre': 'Orion (IA)'
    }
}

# ============================================================
# DETECCIÓN DE PERFIL
# ============================================================

def detectar_perfil(user_message, perfil_especifico=None):
    if perfil_especifico and perfil_especifico in PERFILES:
        return perfil_especifico
    
    texto = user_message.lower()
    
    for perfil_id, data in PERFILES.items():
        for palabra in data["palabras_clave"]:
            if palabra in texto:
                return perfil_id
    
    return "lucia"

def detectar_especialidad(texto):
    texto_lower = texto.lower()
    mapeo = {
        'gps': ['gps', 'rastreo', 'flota', 'geocerca', 'vehículo'],
        'cctv': ['cámara', 'video', 'vigilancia', 'cctv', 'movimiento'],
        'access': ['acceso', 'biometría', 'huella', 'qr', 'control acceso'],
        'chip_taxi': ['taxi', 'viaje', 'app taxi', 'conductor'],
        'soporte': ['falla', 'error', 'problema', 'no funciona']
    }
    for especialidad, palabras in mapeo.items():
        for palabra in palabras:
            if palabra in texto_lower:
                return especialidad
    return None

def get_agente_por_especialidad(especialidad):
    mapeo = {
        'gps': AGENTE_AGATA_ID,       # 53 (Ágata)
        'chip_taxi': AGENTE_AGATA_ID, # 53 (Ágata)
        'cctv': AGENTE_LUCIA_ID,      # 54 (Lucía)
        'access': AGENTE_LUCIA_ID,    # 54 (Lucía)
        'soporte': AGENTE_ORION_ID    # 55 (Orion)
    }
    return mapeo.get(especialidad, AGENTE_LUCIA_ID)

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
        print(f"❌ Error IMAP para {email_user}: {e}")
        return None

def procesar_correos():
    resultados = []
    
    # Procesar correos de ORION (Soporte)
    resultados.append(procesar_una_cuenta(EMAIL_USER, EMAIL_PASSWORD, "Orion"))
    
    # Procesar correos de LUCÍA (Ventas)
    resultados.append(procesar_una_cuenta(EMAIL_VENTAS, EMAIL_VENTAS_PASSWORD, "Lucía"))
    
    return {
        'success': True,
        'message': f"Procesados: {len(resultados)} cuentas",
        'resultados': resultados
    }

# ============================================================
# FUNCIÓN PARA CREAR TAREA EN BD
# ============================================================

def crear_tarea_en_bd(remitente, asunto, agente_id):
    try:
        import mysql.connector
        conn = mysql.connector.connect(
            host=os.environ.get('DB_HOST'),
            user=os.environ.get('DB_USER'),
            password=os.environ.get('DB_PASSWORD'),
            database=os.environ.get('DB_NAME', 'u416165369_corella_crm')
        )
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO tareas (texto, fecha_limite, asignada_por, asignada_a, fuente)
            VALUES (%s, DATE_ADD(CURDATE(), INTERVAL 1 DAY), %s, %s, 'correo')
        """, (f"Correo de {remitente}: {asunto[:50]}...", 1, agente_id))
        conn.commit()
        cursor.close()
        conn.close()
        print(f"✅ Tarea creada para agente {agente_id}")
    except Exception as e:
        print(f"❌ Error creando tarea: {e}")

def procesar_una_cuenta(email_user, email_password, nombre_agente):
    mail = conectar_imap(email_user, email_password)
    if not mail:
        return {'cuenta': email_user, 'status': 'error', 'message': 'No se pudo conectar'}
    
    try:
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        
        if not email_ids:
            mail.close()
            mail.logout()
            return {'cuenta': email_user, 'status': 'ok', 'procesados': 0}
        
        procesados = 0
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
                
                texto_completo = f"{asunto}\n{cuerpo}"
                especialidad = detectar_especialidad(texto_completo)
                
                # Asignar agente según la cuenta de correo
                if "ventas" in email_user:
                    agente_id = AGENTE_LUCIA_ID  # 54
                    perfil = "lucia"
                else:
                    agente_id = AGENTE_ORION_ID   # 55
                    perfil = "orion"
                
                # Crear tarea en la BD
                crear_tarea_en_bd(remitente, asunto, agente_id)
                
                # Generar y enviar respuesta
                respuesta = generar_respuesta(cuerpo, perfil)
                if enviar_correo(remitente, f"Re: {asunto}", respuesta, email_user, email_password):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    procesados += 1
                
            except Exception as e:
                print(f"❌ Error procesando correo en {email_user}: {e}")
                continue
        
        mail.close()
        mail.logout()
        return {'cuenta': email_user, 'status': 'ok', 'procesados': procesados}
        
    except Exception as e:
        return {'cuenta': email_user, 'status': 'error', 'message': str(e)}
        
def generar_respuesta(user_message, perfil):
    try:
        import ollama
        perfil_data = PERFILES.get(perfil, PERFILES["lucia"])
        full_prompt = f"{perfil_data['prompt']}\n\nCliente: {user_message}\n\nAsistente:"
        response = ollama.generate(
            model='llama3.2:latest',
            prompt=full_prompt,
            options={'temperature': 0.3}
        )
        if response and response.get('response'):
            return response['response']
    except:
        pass
    return FALLBACK_RESPUESTAS.get(perfil, FALLBACK_RESPUESTAS["lucia"])


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
        'success': resultado['success'],
        'message': resultado.get('message', ''),
        'procesados': resultado.get('procesados', 0),
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
# FUNCIÓN PARA ENVIAR CORREO
# ============================================================

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
        print(f"✅ Correo enviado a {para}")
        return True
    except Exception as e:
        print(f"❌ Error SMTP: {e}")
        return False

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
                print("💓 Heartbeat enviado")
            else:
                print(f"⚠️ Heartbeat falló: {response.status_code}")
        except Exception as e:
            print(f"❌ Heartbeat falló: {e}")
        time.sleep(30)

# Iniciar el heartbeat en un hilo separado
threading.Thread(target=enviar_heartbeat, daemon=True).start()

def leer_correos():
    """Lee correos no leídos de ambas cuentas"""
    cuentas = [
        {'email': EMAIL_USER, 'password': EMAIL_PASSWORD, 'nombre': 'Orion'},
        {'email': EMAIL_VENTAS, 'password': EMAIL_VENTAS_PASSWORD, 'nombre': 'Lucía'}
    ]
    
    for cuenta in cuentas:
        logger.info(f"📡 Revisando cuenta: {cuenta['email']}")
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
            mail.login(cuenta['email'], cuenta['password'])
            mail.select('INBOX')
            
            result, data = mail.search(None, 'UNSEEN')
            correos_ids = data[0].split()
            
            logger.info(f"📧 {cuenta['email']}: {len(correos_ids)} correos no leídos")
            
            for email_id in correos_ids:
                procesar_correo_individual(mail, email_id, cuenta['nombre'])
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"❌ Error en cuenta {cuenta['email']}: {e}")

def procesar_correo_individual(mail, email_id, nombre_cuenta):
    """Procesa un correo individual y asigna tarea"""
    try:
        result, msg_data = mail.fetch(email_id, '(RFC822)')
        msg = email.message_from_bytes(msg_data[0][1])
        
        remitente = msg['From']
        asunto = msg['Subject']
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
            if nombre_cuenta == 'Orion':
                especialidad = 'soporte'
            else:
                especialidad = 'cctv'  # Default para ventas
        
        if especialidad and especialidad in ESPECIALIDADES:
            agente = ESPECIALIDADES[especialidad]
            logger.info(f"✅ Asignando a {agente['nombre']} (ID: {agente['agente_id']})")
            
            # Crear tarea en la BD
            try:
                conn = mysql.connector.connect(
                    host=DB_HOST,
                    user=DB_USER,
                    password=DB_PASSWORD,
                    database=DB_NAME
                )
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tareas (texto, fecha_limite, asignada_por, asignada_a, fuente)
                    VALUES (%s, DATE_ADD(CURDATE(), INTERVAL 1 DAY), %s, %s, 'correo')
                """, (f"Correo de {remitente}: {asunto}", 1, agente['agente_id']))
                conn.commit()
                tarea_id = cursor.lastrowid
                cursor.close()
                conn.close()
                logger.info(f"📋 Tarea creada (ID: {tarea_id})")
            except Exception as e:
                logger.error(f"❌ Error creando tarea: {e}")
            
            # Generar respuesta
            prompt_data = obtener_prompt_agente(agente['agente_id'])
            respuesta = responder_con_ollama(
                prompt_data['prompt_sistema'], 
                cuerpo, 
                prompt_data['modelo'],
                prompt_data.get('temperatura', 0.3)
            )
            
            # Enviar respuesta
            enviar_respuesta(remitente, asunto, respuesta)
            logger.info(f"✉️ Respuesta enviada a {remitente}")
            
            # Marcar como leído
            mail.store(email_id, '+FLAGS', '\\Seen')
        else:
            logger.warning("⚠️ No se pudo clasificar el correo")
            
    except Exception as e:
        logger.error(f"❌ Error procesando correo: {e}")

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
    app.run(host='0.0.0.0', port=PORT, debug=False)
