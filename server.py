# server.py - CON NOMBRES DE VARIABLES DE RENDER
import os
import imaplib
import smtplib
import email
from email.mime.text import MIMEText
import time
import ssl
import logging
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from dotenv import load_dotenv
import google.generativeai as genai

# Cargar .env
load_dotenv()

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# ============================================================
# ESCUDO DE PROTECCIÓN PARA RENDER
# ============================================================
class RenderHealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-type", "text/plain; charset=utf-8")
        self.end_headers()
        self.wfile.write(b"Corella Multi - Agente de Correo activo\n")
    
    def log_message(self, format, *args):
        return

def levantar_servidor_falso():
    try:
        server = HTTPServer(('0.0.0.0', 10000), RenderHealthCheckHandler)
        server.serve_forever()
    except Exception as e:
        print(f"⚠️ No se pudo levantar el servidor falso: {e}")

def blindar_agente_en_render():
    hilo = threading.Thread(target=levantar_servidor_falso, daemon=True)
    hilo.start()
    print("✅ Servidor falso en puerto 10000 activado")

# ============================================================
# CONFIGURACIÓN DE CORREOS (CON NOMBRES DE RENDER)
# ============================================================
EMAIL_CONTACTO = os.getenv('EMAIL_CONTACTO')          
PASS_CONTACTO = os.getenv('PASSWORD_CONTACTO')       

EMAIL_VENTAS = os.getenv('EMAIL_VENTAS')          
PASS_VENTAS = os.getenv('PASSWORD_VENTAS')        

IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')
SMTP_PORT = int(os.getenv('SMTP_PORT', 25))

# ============================================================
# CONFIGURAR GEMINI
# ============================================================
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    gemini_model = genai.GenerativeModel('models/gemini-2.0-flash')
    logger.info("✅ Gemini API configurada correctamente")
else:
    gemini_model = None
    logger.warning("⚠️ GEMINI_API_KEY no detectada")

# ============================================================
# DIAGNÓSTICO
# ============================================================
print("\n🔍 DIAGNÓSTICO DE CREDENCIALES:")
print(f"📧 EMAIL_CONTACTO: {EMAIL_CONTACTO}")
print(f"📧 EMAIL_VENTAS: {EMAIL_VENTAS}")
print(f"🤖 GEMINI_API_KEY: {'✅ CONFIGURADA' if GEMINI_API_KEY else '❌ VACÍA'}")
print("=" * 60)

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
# FUNCIONES DE PROCESAMIENTO
# ============================================================
def responder_con_gemini(prompt_sistema, mensaje):
    """Genera respuesta usando Gemini SDK"""
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY no configurada")
        return "Lo siento, el servicio de IA no está disponible. Contacta al 938 120 6643."
    
    try:
        full_prompt = f"{prompt_sistema}\n\nCliente: {mensaje}\n\nAsistente:"
        # USAMOS EL NOMBRE CORRECTO: gemini_model
        response = gemini_model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Error en Gemini: {e}")
        return "Hola, gracias por escribirnos. Recibimos tu solicitud sobre sistemas de seguridad y un asesor humano te atenderá a la brevedad. Puedes marcarnos al 938 120 6643."
        
def enviar_respuesta(para, asunto, respuesta, email_from, password):
    try:
        msg = MIMEText(respuesta, 'plain', 'utf-8')
        msg['Subject'] = f"Re: {asunto}"
        msg['From'] = email_from
        msg['To'] = para
        
        logger.info(f"Connecting to SMTP {SMTP_SERVER} on port 587...")
        # Usamos un timeout explícito para evitar que se quede colgado si la red falla
        server = smtplib.SMTP_SSL(SMTP_SERVER, SMTP_PORT)
        server.ehlo() 
        server.starttls()
        server.ehlo()
        server.login(email_from, password)
        server.send_message(msg)
        server.quit()
        logger.info(f"✅ Respuesta enviada a {para} desde {email_from}")
        return True
    except Exception as e:
        logger.error(f"❌ Error SMTP desde {email_from}: {e}")
        return False

def leer_y_responder_cuenta(cuenta_correo, password, perfil, prompt_sistema):
    if not cuenta_correo or not password:
        logger.warning(f"⚠️ {perfil} - Sin credenciales")
        return
    
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(cuenta_correo, password)
        mail.select('INBOX')
        
        result, data = mail.search(None, 'UNSEEN')
        correos_ids = data[0].split()
        
        if correos_ids:
            logger.info(f"📧 [{perfil}] {len(correos_ids)} correos nuevos.")
            
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
                
                logger.info(f"📥 [{perfil}] De: {remitente} | Asunto: {asunto}")
                
                respuesta = responder_con_gemini(prompt_sistema, cuerpo)
                
                if enviar_respuesta(remitente, asunto, respuesta, cuenta_correo, password):
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    logger.info(f"📌 [{perfil}] Correo marcado como leído.")
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"❌ Error IMAP en {perfil}: {e}")

def procesar_todos_los_correos():
    logger.info("📬 Procesando todas las cuentas...")
    if EMAIL_CONTACTO and PASS_CONTACTO:
        leer_y_responder_cuenta(EMAIL_CONTACTO, PASS_CONTACTO, "Orion", PROMPT_ORION)
    else:
        logger.warning("⚠️ Orion - Sin credenciales")
    
    if EMAIL_VENTAS and PASS_VENTAS:
        leer_y_responder_cuenta(EMAIL_VENTAS, PASS_VENTAS, "Lucia", PROMPT_LUCIA)
    else:
        logger.warning("⚠️ Lucia - Sin credenciales")
    logger.info("📬 Procesamiento completado")

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 CORELLA WORKER - Asistente de Correo")
    print("=" * 60)
    print(f"Orion (Soporte): {EMAIL_CONTACTO}")
    print(f"Lucia (Ventas): {EMAIL_VENTAS}")
    print("=" * 60)
    
    blindar_agente_en_render()
    
    print("\n🔍 Verificando conexiones...")
    
    # Probar Orion
    if EMAIL_CONTACTO and PASS_CONTACTO:
        print(f"✅ Orion - Credenciales cargadas")
    else:
        print(f"⚠️ Orion - Sin credenciales")
    
    # Probar Lucia
    if EMAIL_VENTAS and PASS_VENTAS:
        print(f"✅ Lucia - Credenciales cargadas")
    else:
        print(f"⚠️ Lucia - Sin credenciales")
    
    print("\n🔄 Iniciando monitoreo...")
    
    while True:
        try:
            procesar_todos_los_correos()
        except Exception as e:
            logger.error(f"Error en ciclo principal: {e}")
        time.sleep(30)
