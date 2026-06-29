import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import requests
import time
import ssl
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv

# Cargar variables de entorno (.env)
load_dotenv()

# Configurar logging idéntico a tu ejemplo
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN DE CREDENCIALES (2 AGENTES)
# =====================================================
# AGENTE 1: Orion (Soporte / Contacto) - Usa tus variables actuales
EMAIL_ORION = os.getenv('EMAIL_USER')  
PASS_ORION = os.getenv('EMAIL_PASS')

# AGENTE 2: Lucía (Ventas) - Agrega estas en tu Render si usas dos correos distintos
EMAIL_LUCIA = os.getenv('EMAIL_USER_VENTAS') or os.getenv('EMAIL_USER') # Si es el mismo correo, usará el principal
PASS_LUCIA = os.getenv('EMAIL_PASS_VENTAS') or os.getenv('EMAIL_PASS')

IMAP_SERVER = os.getenv('IMAP_SERVER')
SMTP_SERVER = os.getenv('SMTP_SERVER')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# =====================================================
# PROMPTS DEL SISTEMA PARA CADA AGENTE
# =====================================================
PROMPT_ORION = """
Eres Orion, especialista en soporte técnico de SATEC Network.
Atiendes las dudas técnicas de los clientes.

SATEC ofrece soporte para:
1. GPS: Rastreo satelital, geocercas, corte de motor, localización de flotas.
2. CCTV: Cámaras de videovigilancia, grabación, monitoreo perimetral, IA.
3. Control de Acceso: Biometría, huella digital, QR, tarjetas, lectores.
4. Chip Taxi: App para taxis, viajes, conductores.

Responde de forma técnica, paciente, clara y amable.
Si el cliente quiere comprar o cotizar, sugiere contactar a ventas@satecnetwork.com.
Teléfono de soporte: 938 120 6643.
"""

PROMPT_LUCIA = """
Eres Lucía, asesora comercial y de ventas de SATEC Network.
Tu objetivo es brindar información de precios y cerrar ventas.

Precios de referencia de SATEC:
1. GPS: Desde $500/mes por vehículo.
2. CCTV: Paquetes desde $3,000 (4 cámaras + DVR).
3. Control de Acceso: Desde $2,500 por punto de acceso.
4. Chip Taxi: Plan desde $300/mes por unidad.

Responde de forma entusiasta, persuasiva, vendedora y muy amable.
Si es una falla técnica compleja, sugiere contactar a soporte@satecnetwork.com.
Teléfono de ventas: 938 120 6643.
"""

# ============================================================
# ESCUDO DE PROTECCIÓN PARA RENDER (ÁNGEL GUARDIAN)
# ============================================================
class RenderHealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Corella Multi-Agente Activo\n")
    def log_message(self, format, *args):
        return

def levantar_servidor_falso():
    try:
        server = HTTPServer(('0.0.0.0', 10000), RenderHealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        logger.error(f"⚠️ Error en servidor de Render: {e}")

# =====================================================
# FUNCIONES DE CONEXIÓN E INTELIGENCIA ARTIFICIAL
# =====================================================
def test_conexion(email_user, password, perfil):
    """Prueba conexión IMAP básica para asegurar que las credenciales funcionan"""
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(email_user, password)
        mail.select('INBOX')
        mail.close()
        mail.logout()
        print(f"✅ Conexión exitosa para Agente {perfil} ({email_user})")
        return True
    except Exception as e:
        print(f"❌ Error de conexión para Agente {perfil}: {e}")
        return False

def responder_con_gemini(prompt_sistema, mensaje_cliente):
    """Genera la respuesta usando la API de Gemini"""
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{prompt_sistema}\n\nCliente: {mensaje_cliente}\n\nRespuesta:"
                }]
            }]
        }
        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()
        return response_json['candidates'][0]['content']['parts'][0]['text']
    except Exception as e:
        logger.error(f"❌ Error en Gemini: {e}")
        return "Lo siento, estamos presentando interrupciones técnicas. Por favor contáctanos al 938 120 6643."

def enviar_respuesta(para, asunto, respuesta, de_correo, de_password):
    """Envía el correo saliente usando la cuenta del agente correspondiente"""
    try:
        msg = MIMEText(respuesta, 'plain', 'utf-8')
        msg['Subject'] = f"Re: {asunto}"
        msg['From'] = de_correo
        msg['To'] = para
        
        server = smtplib.SMTP(SMTP_SERVER, 587)
        server.starttls()
        server.login(de_correo, de_password)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Correo enviado a {para} desde {de_correo}")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando correo: {e}")
        return False

# =====================================================
# LÓGICA DE PROCESAMIENTO POR AGENTE
# =====================================================
def leer_y_responder_agente(email_user, password, perfil, prompt_sistema):
    """Busca correos no leídos en la cuenta asignada y responde con su perfil"""
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(email_user, password)
        mail.select('INBOX')
        
        # Buscar correos NO LEÍDOS
        result, data = mail.search(None, 'UNSEEN')
        correos_ids = data[0].split()
        
        logger.info(f"📧 [{perfil}] Correos no leídos: {len(correos_ids)}")
        
        for email_id in correos_ids:
            logger.info(f"📥 [{perfil}] Procesando correo ID: {email_id}")
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
            
            # Generar respuesta con Gemini usando el prompt del agente actual
            logger.info(f"🤖 [{perfil}] Generando respuesta con Gemini...")
            respuesta = responder_con_gemini(prompt_sistema, cuerpo)
            
            # Enviar usando sus propias credenciales
            enviar_respuesta(remitente, asunto, respuesta, email_user, password)
            
            # Marcar como leído
            mail.store(email_id, '+FLAGS', '\\Seen')
            logger.info(f"✅ [{perfil}] Respondido y marcado como leído.")
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"❌ Error en el proceso del agente {perfil}: {e}")

# =====================================================
# PROGRAMA PRINCIPAL
# =====================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 SATEC NETWORK - Sistema Multi-Agente (Orion & Lucía)")
    print("=" * 60)
    
    # Levantar el validador de Render en segundo plano
    threading.Thread(target=levantar_servidor_falso, daemon=True).start()
    
    print("\n🔍 Verificando credenciales del sistema...")
    orion_ok = test_conexion(EMAIL_ORION, PASS_ORION, "Orion (Soporte)")
    
    # Solo testea a Lucía si configuraste un correo diferente para ventas
    lucia_ok = True
    if EMAIL_LUCIA != EMAIL_ORION:
        lucia_ok = test_conexion(EMAIL_LUCIA, PASS_LUCIA, "Lucía (Ventas)")
        
    print("\n⏱️ Iniciando ciclo de monitoreo cada 30 segundos...\n")
    
    while True:
        try:
            # 🔧 EJECUTA AGENTE 1: ORION
            if EMAIL_ORION and PASS_ORION:
                logger.info(f"📡 Conectando Agente Orion a {EMAIL_ORION}...")
                leer_y_responder_agente(EMAIL_ORION, PASS_ORION, "Orion", PROMPT_ORION)
            
            # 💬 EJECUTA AGENTE 2: LUCÍA
            # Si EMAIL_USER_VENTAS está vacío, procesará el mismo correo pero con perfil de ventas
            if EMAIL_LUCIA and PASS_LUCIA:
                logger.info(f"📡 Conectando Agente Lucía a {EMAIL_LUCIA}...")
                leer_y_responder_agente(EMAIL_LUCIA, PASS_LUCIA, "Lucía", PROMPT_LUCIA)
                
            time.sleep(30)
            
        except KeyboardInterrupt:
            print("\n🛑 Sistema detenido.")
            break
        except Exception as e:
            logger.error(f"❌ Error general en el bucle: {e}")
            time.sleep(10)
