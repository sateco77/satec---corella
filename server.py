# server.py - VERSIÓN WORKER PROFESIONAL
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import time
import ssl
import logging
from dotenv import load_dotenv
import google.generativeai as genai

# Cargar .env
load_dotenv()

# Configurar logging para ver todo en Render en tiempo real
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# CONFIGURACIÓN DE CORREOS
# ============================================================
EMAIL_CONTACTO = os.getenv('EMAIL_USER') or os.getenv('EMAIL_USER_CONTACTO')
PASS_CONTACTO = os.getenv('EMAIL_PASSWORD') or os.getenv('EMAIL_PASS_CONTACTO')

EMAIL_VENTAS = os.getenv('EMAIL_VENTAS')
PASS_VENTAS = os.getenv('PASSWORD_VENTAS')

IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')

# Configuración de Gemini
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("✅ Gemini API configurada correctamente")
else:
    logger.warning("⚠️ GEMINI_API_KEY no detectada")

# ============================================================
# PROMPTS DE LOS AGENTES
# ============================================================
PROMPT_ORION = """
Eres Orion, especialista en soporte técnico de SATEC Network.
Atiendes el correo contacto@satecnetwork.com.

SATEC ofrece soporte para:
1. GPS: Rastreo satelital, geocercas, corte de motor, localización de flotas.
2. CCTV: Cámaras de videovigilancia, grabación, monitoreo perimetral, IA.
3. Control de Acceso: Biometría, huella digital, QR, tarjetas, lectores.
4. Chip Taxi: App para taxis, viajes, conductores.

Responde de forma clara y técnica, pero amable.
Si es una cotización o intención de compra, deriva a ventas@satecnetwork.com.
Teléfono: 938 120 6643.
"""

PROMPT_LUCIA = """
Eres Lucía, asesora comercial de SATEC Network.
Atiendes el correo ventas@satecnetwork.com.

Precios de referencia SATEC:
1. GPS: Desde $500/mes por vehículo
2. CCTV: Paquetes desde $3,000 (4 cámaras + DVR)
3. Control de Acceso: Desde $2,500 por punto de acceso
4. Chip Taxi: Plan desde $300/mes por unidad

Siempre ofrece soluciones y menciona promociones.
Si es un problema técnico complejo, deriva a soporte@satecnetwork.com.
Teléfono: 938 120 6643.
"""

# ============================================================
# FUNCIONES NATIVAS DE PROCESAMIENTO
# ============================================================
def responder_con_gemini(prompt_sistema, mensaje):
    if not GEMINI_API_KEY:
        return "Lo siento, el servicio de IA no está disponible temporalmente. Contacta al 938 120 6643."
    try:
        full_prompt = f"{prompt_sistema}\n\nCliente: {mensaje}\n\nAsistente:"
        response = gemini_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Error en Gemini: {e}")
        return "Lo siento, estamos experimentando interrupciones. Por favor contáctanos al 938 120 6643."

def enviar_respuesta(para, asunto, respuesta, email_from, password):
    try:
        msg = MIMEText(respuesta, 'plain', 'utf-8')
        msg['Subject'] = f"Re: {asunto}"
        msg['From'] = email_from
        msg['To'] = para
        
        server = smtplib.SMTP(SMTP_SERVER, 587)
        server.starttls()
        server.login(email_from, password)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Correo saliente enviado con éxito a {para}")
        return True
    except Exception as e:
        logger.error(f"❌ Error de envío SMTP desde {email_from}: {e}")
        return False

def leer_y_responder_cuenta(cuenta_correo, password, perfil, prompt_sistema):
    if not cuenta_correo or not password:
        return
    
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(cuenta_correo, password)
        mail.select('INBOX')
        
        result, data = mail.search(None, 'UNSEEN')
        correos_ids = data[0].split()
        
        if correos_ids:
            logger.info(f"📧 [{perfil}] Encontrados {len(correos_ids)} correos nuevos.")
            
            for email_id in correos_ids:
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
                
                logger.info(f"📥 [{perfil}] Procesando de: {remitente} | Asunto: {asunto}")
                
                # Inteligencia Artificial
                respuesta = responder_con_gemini(prompt_sistema, cuerpo)
                
                # Réplica
                if enviar_respuesta(remitente, asunto, respuesta, cuenta_correo, password):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    logger.info(f"📌 [{perfil}] Correo ID {email_id} marcado como leído.")
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"❌ Error de conexión IMAP en cuenta {perfil}: {e}")

# ============================================================
# BUCLE PRINCIPAL DEL WORKER
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 CORELLA WORKER INSTALADO Y CORRIENDO")
    print("=" * 60)
    print(f"🔧 Perfil Soporte (Orion): {EMAIL_CONTACTO}")
    print(f"💬 Perfil Ventas (Lucía):  {EMAIL_VENTAS}")
    print("=" * 60)

    while True:
        try:
            # Procesar Agente 1: Orion
            if EMAIL_CONTACTO and PASS_CONTACTO:
                leer_y_responder_cuenta(EMAIL_CONTACTO, PASS_CONTACTO, "Orion", PROMPT_ORION)
            
            # Procesar Agente 2: Lucía
            if EMAIL_VENTAS and PASS_VENTAS:
                leer_y_responder_cuenta(EMAIL_VENTAS, PASS_VENTAS, "Lucía", PROMPT_LUCIA)
                
        except Exception as e:
            logger.error(f"⚠️ Error en el ciclo general del Worker: {e}")
            
        # Esperar 30 segundos antes de volver a consultar las bandejas
        time.sleep(30)
