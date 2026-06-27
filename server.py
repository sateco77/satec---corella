#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA Multiperfil para SATEC NETWORK
Unificado: Chat + Procesamiento de correos + Asignación de tareas
"""

import os
import json
import requests
import subprocess
import imaplib
import smtplib
import email
import ssl
import logging
from email.mime.text import MIMEText
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from datetime import datetime

# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__, static_folder='web')

@app.route('/')
def home():
    return send_from_directory('web', 'index.html')

CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# CONFIGURACIÓN DE CORREO (desde variables de entorno)
# ============================================================

EMAIL_USER = os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', '')
IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')

# IDs de agentes en la base de datos
AGENTE_AGATA_ID = int(os.environ.get('AGENTE_AGATA_ID', 4))
AGENTE_LUCIA_ID = int(os.environ.get('AGENTE_LUCIA_ID', 5))
AGENTE_ORION_ID = int(os.environ.get('AGENTE_ORION_ID', 6))

# ============================================================
# PERFILES DE AGENTES (igual que antes)
# ============================================================

PERFILES = {
    "agata": {
        "id": "agata",
        "nombre": "Ágata",
        "rol": "Ventas y Marketing",
        "emoji": "📊",
        "color": "#8B5CF6",
        "palabras_clave": ["comprar", "cotizar", "precio", "oferta", "descuento", "promocion", "venta", "costo"],
        "prompt": """Eres ÁGATA, experta en Ventas y Marketing de SATEC. Tono persuasivo y entusiasta. Destaca promociones."""
    },
    "lucia": {
        "id": "lucia",
        "nombre": "Lucía",
        "rol": "Atención al Cliente",
        "emoji": "💬",
        "color": "#3B82F6",
        "palabras_clave": ["demo", "ayuda", "duda", "consultar", "atencion", "cliente", "servicio"],
        "prompt": """Eres LUCÍA, experta en Atención al Cliente de SATEC. Tono cálido y empático. Ofrece soluciones claras."""
    },
    "orion": {
        "id": "orion",
        "nombre": "Orion",
        "rol": "Soporte Técnico",
        "emoji": "🔧",
        "color": "#F59E0B",
        "palabras_clave": ["falla", "error", "problema", "no funciona", "instalar", "configurar", "técnico"],
        "prompt": """Eres ORION, experto en Soporte Técnico de SATEC. Tono técnico pero claro. Da pasos concretos."""
    }
}

FALLBACK_RESPUESTAS = {
    "agata": "📊 ¡Gracias por contactar a SATEC! Soy Ágata, tu asesora de ventas. ¿Te gustaría conocer nuestras promociones? 🚀",
    "lucia": "💬 Soy Lucía, tu asesora de atención al cliente. ¿En qué puedo ayudarte hoy? ❤️",
    "orion": "🔧 Soy Orion, tu técnico de soporte. ¿Puedes darme más detalles sobre el problema? 💻"
}

# ============================================================
# DETECCIÓN DE PERFIL
# ============================================================

def detectar_perfil(user_message, perfil_especifico=None):
    """Detecta qué perfil usar según el mensaje"""
    if perfil_especifico and perfil_especifico in PERFILES:
        return perfil_especifico
    
    texto = user_message.lower()
    
    # Si se menciona un nombre específico
    if "agata" in texto or "ventas" in texto:
        return "agata"
    if "orion" in texto or "soporte" in texto or "técnico" in texto:
        return "orion"
    if "lucia" in texto or "atencion" in texto:
        return "lucia"
    
    # Detección por palabras clave
    for perfil_id, data in PERFILES.items():
        for palabra in data["palabras_clave"]:
            if palabra in texto:
                return perfil_id
    
    return "lucia"

def detectar_especialidad(texto):
    """Detecta especialidad para asignación de tareas"""
    texto_lower = texto.lower()
    
    mapeo = {
        'gps': ['gps', 'rastreo', 'flota', 'geocerca', 'corte motor', 'vehículo'],
        'cctv': ['cámara', 'video', 'vigilancia', 'cctv', 'movimiento', 'perimetral'],
        'access': ['acceso', 'biometría', 'huella', 'qr', 'tarjeta', 'control acceso'],
        'chip_taxi': ['taxi', 'viaje', 'app taxi', 'conductor'],
        'soporte': ['falla', 'error', 'problema', 'no funciona', 'avería', 'bug']
    }
    
    for especialidad, palabras in mapeo.items():
        for palabra in palabras:
            if palabra in texto_lower:
                return especialidad
    
    return None

def get_agente_por_especialidad(especialidad):
    """Retorna el ID del agente según la especialidad"""
    mapeo = {
        'gps': AGENTE_AGATA_ID,
        'chip_taxi': AGENTE_AGATA_ID,
        'cctv': AGENTE_LUCIA_ID,
        'access': AGENTE_LUCIA_ID,
        'soporte': AGENTE_ORION_ID
    }
    return mapeo.get(especialidad, AGENTE_LUCIA_ID)

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
        print(f"❌ Error conectando IMAP: {e}")
        return None

def enviar_correo(para, asunto, mensaje):
    """Envía un correo usando SMTP"""
    try:
        msg = MIMEText(mensaje, 'plain', 'utf-8')
        msg['Subject'] = asunto
        msg['From'] = EMAIL_USER
        msg['To'] = para
        
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(SMTP_SERVER, 465, context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        return True
    except Exception as e:
        print(f"❌ Error enviando correo: {e}")
        return False

# ============================================================
# GENERAR RESPUESTA
# ============================================================

def generar_respuesta(user_message, perfil):
    """Genera respuesta usando el perfil seleccionado"""
    try:
        # Intentar con Ollama primero
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
    
    # Fallback
    return FALLBACK_RESPUESTAS.get(perfil, FALLBACK_RESPUESTAS["lucia"])

# ============================================================
# PROCESAR CORREOS
# ============================================================

def procesar_correos():
    """Procesa correos no leídos y asigna tareas a los agentes"""
    mail = conectar_imap()
    if not mail:
        return {"success": False, "message": "Error conectando al correo"}
    
    try:
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        
        if not email_ids:
            mail.close()
            mail.logout()
            return {"success": True, "message": "No hay correos nuevos", "procesados": 0}
        
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
                agente_id = get_agente_por_especialidad(especialidad)
                
                # Crear tarea en la base de datos
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
                except Exception as e:
                    print(f"❌ Error creando tarea: {e}")
                
                # Generar respuesta automática
                perfil_detectado = detectar_perfil(texto_completo)
                respuesta = generar_respuesta(cuerpo, perfil_detectado)
                
                # Enviar respuesta
                if enviar_correo(remitente, f"Re: {asunto}", respuesta):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    procesados += 1
                
            except Exception as e:
                print(f"❌ Error procesando correo: {e}")
                continue
        
        mail.close()
        mail.logout()
        return {"success": True, "message": f"{procesados} correos procesados", "procesados": procesados}
        
    except Exception as e:
        return {"success": False, "message": str(e)}

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
    """Chat en tiempo real con detección de perfil"""
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
    """Endpoint para procesar correos manualmente o vía CRON"""
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
            'emoji': data['emoji'],
            'color': data['color']
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
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA Multiperfil Unificado")
    print("=" * 60)
    print("📊 Perfiles disponibles:")
    for key, data in PERFILES.items():
        print(f"   {data['emoji']} {data['nombre']} ({data['rol']})")
    print("=" * 60)
    print(f"📧 Correo: {EMAIL_USER}")
    print(f"🌐 Puerto: {PORT}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
