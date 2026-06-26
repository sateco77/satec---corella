# soporte_worker_api.py - Worker de soporte para ORION (API para Web Service)
from flask import Flask, request, jsonify
import os
import imaplib
import smtplib
import mysql.connector
import json
import ssl
import logging
import re
import time
from email.mime.text import MIMEText
from datetime import datetime

app = Flask(__name__)

# ============================================================
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
# ============================================================

DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME', 'u416165369_corella_crm')

EMAIL_USER = os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))

# IDs de los agentes IA
AGENTE_AGATA_ID = int(os.environ.get('AGENTE_AGATA_ID', 53))
AGENTE_LUCIA_ID = int(os.environ.get('AGENTE_LUCIA_ID', 54))
AGENTE_ORION_ID = int(os.environ.get('AGENTE_ORION_ID', 55))

# ============================================================
# LOGGING
# ============================================================

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONEXIÓN A BASE DE DATOS
# ============================================================

def get_db_connection():
    """Retorna conexión a la base de datos"""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# ============================================================
# ESPECIALIDADES Y AGENTES
# ============================================================

ESPECIALIDADES = {
    'gps': {
        'palabras': ['gps', 'rastreo', 'flota', 'geocerca', 'corte motor', 'localización', 'vehículo', 'tracking'],
        'agente_id': AGENTE_AGATA_ID,
        'nombre': 'Ágata (IA)'
    },
    'cctv': {
        'palabras': ['cámara', 'video', 'vigilancia', 'cctv', 'movimiento', 'perimetral', 'grabación', 'ia', 'reconocimiento'],
        'agente_id': AGENTE_LUCIA_ID,
        'nombre': 'Lucía (IA)'
    },
    'access': {
        'palabras': ['acceso', 'biometría', 'huella', 'qr', 'tarjeta', 'lector', 'control acceso', 'credencial'],
        'agente_id': AGENTE_ORION_ID,
        'nombre': 'Orion (IA)'
    },
    'chip_taxi': {
        'palabras': ['taxi', 'viaje', 'app', 'conductor', 'chip taxi', 'pasajero', 'solicitar viaje', 'tarifa'],
        'agente_id': AGENTE_AGATA_ID,
        'nombre': 'Ágata (IA)'
    },
    'soporte': {
        'palabras': ['falla', 'error', 'problema', 'no funciona', 'avería', 'bug', 'pantalla', 'conexión', 'red', 'instalación'],
        'agente_id': AGENTE_ORION_ID,
        'nombre': 'Orion (IA)'
    }
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
                logger.info(f"🔍 Especialidad detectada: {esp} → {data['nombre']} (ID: {data['agente_id']})")
                return data
    
    # Por defecto, asignar a Lucía (atención al cliente)
    logger.info("⚠️ No se detectó especialidad, asignando a Lucía")
    return {'agente_id': AGENTE_LUCIA_ID, 'nombre': 'Lucía (IA)'}

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
        logger.info(f"✅ Conectado a IMAP: {EMAIL_USER}")
        return mail
    except Exception as e:
        logger.error(f"❌ Error conectando IMAP: {e}")
        return None

def enviar_respuesta(para, asunto_original, respuesta):
    """Envía respuesta por correo usando SMTP"""
    try:
        msg = MIMEText(respuesta, 'plain', 'utf-8')
        msg['Subject'] = f"Re: {asunto_original}"
        msg['From'] = EMAIL_USER
        msg['To'] = para
        
        context = ssl.create_default_context()
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT, context=context)
        server.login(EMAIL_USER, EMAIL_PASSWORD)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Respuesta enviada a {para}")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando respuesta: {e}")
        return False

def generar_respuesta_ia(agente_id, mensaje_usuario):
    """Genera respuesta usando IA (Ollama)"""
    # Mapeo de prompts por agente
    prompts = {
        AGENTE_AGATA_ID: {
            'system': "Eres ÁGATA, experta en Ventas y Marketing de SATEC. Responde con entusiasmo, destaca promociones y termina con una pregunta.",
            'modelo': 'llama3.2:latest',
            'temperatura': 0.4
        },
        AGENTE_LUCIA_ID: {
            'system': "Eres LUCÍA, experta en Atención al Cliente de SATEC. Responde con calidez, empatía y soluciones claras.",
            'modelo': 'llama3.2:latest',
            'temperatura': 0.3
        },
        AGENTE_ORION_ID: {
            'system': "Eres ORION, experto en Soporte Técnico de SATEC. Diagnostica problemas y da pasos concretos para resolverlos.",
            'modelo': 'llama3.2:latest',
            'temperatura': 0.2
        }
    }
    
    prompt_data = prompts.get(agente_id, prompts[AGENTE_LUCIA_ID])
    
    # Intentar usar Ollama
    try:
        import ollama
        full_prompt = f"{prompt_data['system']}\n\nCliente: {mensaje_usuario}\n\nAsistente:"
        response = ollama.generate(
            model=prompt_data['modelo'],
            prompt=full_prompt,
            options={'temperature': prompt_data['temperatura']}
        )
        return response['response']
    except:
        # Fallback con respuestas predefinidas
        if agente_id == AGENTE_AGATA_ID:
            return "📊 ¡Gracias por contactar a SATEC! Soy Ágata, tu asesora de ventas. ¿Te gustaría conocer nuestras promociones especiales en GPS y CCTV? 🚀"
        elif agente_id == AGENTE_ORION_ID:
            return "🔧 Soy Orion, tu técnico de soporte. ¿Puedes darme más detalles sobre el problema? Así puedo ayudarte mejor. 💻"
        else:
            return "💬 Soy Lucía, tu asesora de atención al cliente. ¿En qué puedo ayudarte hoy? Tenemos servicios de GPS, CCTV, Control de Acceso y CHIP TAXI. ❤️"

# ============================================================
# PROCESAR CORREOS
# ============================================================

def procesar_correos():
    """Procesa correos no leídos y crea tareas para los agentes"""
    mail = conectar_imap()
    if not mail:
        return "❌ Error conectando al correo"
    
    try:
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        
        if not email_ids:
            logger.info("📭 No hay correos nuevos")
            mail.close()
            mail.logout()
            return "📭 No hay correos nuevos"
        
        logger.info(f"📧 {len(email_ids)} correos nuevos")
        
        procesados = 0
        for email_id in email_ids:
            try:
                result, msg_data = mail.fetch(email_id, '(RFC822)')
                msg = email.message_from_bytes(msg_data[0][1])
                
                remitente = msg.get('From', 'Desconocido')
                asunto = msg.get('Subject', 'Sin asunto')
                
                # Extraer cuerpo
                cuerpo = ""
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == 'text/plain':
                            cuerpo = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                            break
                else:
                    cuerpo = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
                
                texto_completo = f"{asunto}\n{cuerpo}"
                agente_info = detectar_especialidad(texto_completo)
                
                logger.info(f"📧 De: {remitente} | Asunto: {asunto[:50]}")
                logger.info(f"✅ Asignando a {agente_info['nombre']} (ID: {agente_info['agente_id']})")
                
                # Crear tarea en la base de datos
                try:
                    conn = get_db_connection()
                    cursor = conn.cursor()
                    cursor.execute("""
                        INSERT INTO tareas (texto, fecha_limite, asignada_por, asignada_a, fuente)
                        VALUES (%s, DATE_ADD(CURDATE(), INTERVAL 1 DAY), %s, %s, 'correo')
                    """, (
                        f"Correo de {remitente}: {asunto[:50]}...",
                        1,  # asignada_por (gerente)
                        agente_info['agente_id']
                    ))
                    conn.commit()
                    tarea_id = cursor.lastrowid
                    cursor.close()
                    conn.close()
                    logger.info(f"📋 Tarea creada (ID: {tarea_id}) para {agente_info['nombre']}")
                except Exception as e:
                    logger.error(f"❌ Error creando tarea: {e}")
                
                # Generar respuesta automática
                respuesta = generar_respuesta_ia(agente_info['agente_id'], cuerpo)
                
                # Enviar respuesta
                if enviar_respuesta(remitente, asunto, respuesta):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    procesados += 1
                    logger.info(f"✉️ Respuesta enviada a {remitente}")
                
            except Exception as e:
                logger.error(f"❌ Error procesando correo: {e}")
                continue
        
        mail.close()
        mail.logout()
        return f"✅ {procesados} correos procesados"
        
    except Exception as e:
        logger.error(f"❌ Error procesando correos: {e}")
        return f"❌ Error: {str(e)}"

# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route('/')
def index():
    return jsonify({
        'service': 'Soporte Worker ORION',
        'status': 'online',
        'version': '2.0',
        'endpoints': {
            'procesar': '/procesar (GET/POST) - Procesa correos de soporte',
            'health': '/health - Verifica el estado del servicio'
        },
        'agentes': {
            'agata': AGENTE_AGATA_ID,
            'lucia': AGENTE_LUCIA_ID,
            'orion': AGENTE_ORION_ID
        }
    })

@app.route('/procesar', methods=['GET', 'POST'])
def procesar_endpoint():
    """Endpoint para procesar correos de soporte"""
    try:
        logger.info("🔄 Procesando correos de soporte...")
        resultado = procesar_correos()
        return jsonify({
            'success': True,
            'resultado': resultado,
            'timestamp': datetime.now().isoformat()
        })
    except Exception as e:
        logger.error(f"❌ Error procesando correos: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/health')
def health():
    return jsonify({
        'status': 'ok',
        'service': 'Soporte Worker ORION',
        'version': '2.0',
        'timestamp': datetime.now().isoformat()
    })

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 10001))
    print("=" * 60)
    print("🔧 SOPORTE WORKER ORION - API")
    print("=" * 60)
    print(f"📧 Email: {EMAIL_USER}")
    print(f"📡 IMAP: {IMAP_SERVER}")
    print("=" * 60)
    print("🤖 Agentes:")
    print(f"   📊 Ágata (ID: {AGENTE_AGATA_ID})")
    print(f"   💬 Lucía (ID: {AGENTE_LUCIA_ID})")
    print(f"   🔧 Orion (ID: {AGENTE_ORION_ID})")
    print("=" * 60)
    print(f"🌐 Servidor en: http://0.0.0.0:{port}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=port, debug=False)
