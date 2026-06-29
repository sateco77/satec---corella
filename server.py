# server.py - CON SDK DE GEMINI
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
# CONFIGURACIÓN DE CORREOS
# ============================================================

EMAIL_CONTACTO = os.getenv('EMAIL_USER_CONTACTO') or os.getenv('EMAIL_USER')
PASS_CONTACTO = os.getenv('EMAIL_PASS_CONTACTO') or os.getenv('EMAIL_PASS')

EMAIL_VENTAS = os.getenv('EMAIL_USER_VENTAS')
PASS_VENTAS = os.getenv('EMAIL_PASS_VENTAS')

IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# ============================================================
# CONFIGURAR GEMINI CON SDK
# ============================================================
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)
    model = genai.GenerativeModel('gemini-1.5-flash')
    logger.info("✅ Gemini API configurada correctamente")
else:
    logger.warning("⚠️ GEMINI_API_KEY no configurada")

# ============================================================
# DIAGNÓSTICO
# ============================================================
print("\n🔍 DIAGNÓSTICO DE CREDENCIALES:")
print(f"📧 EMAIL_CONTACTO: {EMAIL_CONTACTO}")
print(f"📧 EMAIL_VENTAS: {EMAIL_VENTAS}")
print(f"🤖 GEMINI_API_KEY: {'✅ CONFIGURADA' if GEMINI_API_KEY else '❌ VACÍA'}")
print("=" * 60)

# ============================================================
# PERFILES Y PROMPTS
# ============================================================

PROMPT_ORION = """
Eres Orion, especialista en soporte técnico de SATEC Network.
Atiendes el correo contacto@satecnetwork.com.

Tu personalidad:
- Técnico, resolutivo y paciente
- Te enfocas en solucionar problemas
- Das instrucciones claras y paso a paso

SATEC ofrece soporte para:
1. GPS: Rastreo satelital, geocercas, corte de motor, localización de flotas.
2. CCTV: Cámaras de videovigilancia, grabación, monitoreo perimetral, IA.
3. Control de Acceso: Biometría, huella digital, QR, tarjetas, lectores.
4. Chip Taxi: App para taxis, viajes, conductores.

Responde de forma clara y técnica, pero amable.
Si es una cotización, deriva a ventas@satecnetwork.com.
Teléfono: 938 120 6643.
"""

PROMPT_LUCIA = """
Eres Lucía, asesora comercial de SATEC Network.
Atiendes el correo ventas@satecnetwork.com.

Tu personalidad:
- Enfocada en cerrar ventas
- Conoces precios y promociones
- Proactiva y persuasiva

SATEC ofrece:
1. GPS: Desde $500/mes por vehículo
2. CCTV: Paquetes desde $3,000 (4 cámaras + DVR)
3. Control de Acceso: Desde $2,500 por punto de acceso
4. Chip Taxi: Plan desde $300/mes por unidad

Siempre ofrece soluciones y menciona promociones.
Si es un problema técnico, deriva a soporte@satecnetwork.com.
Teléfono: 938 120 6643.
"""

# ============================================================
# FUNCIONES PRINCIPALES
# ============================================================

def test_imap(email, password):
    try:
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(email, password)
        mail.select('INBOX')
        mail.close()
        mail.logout()
        return True
    except Exception as e:
        logger.error(f"❌ IMAP Error para {email}: {e}")
        return False

def test_smtp(email, password):
    try:
        server = smtplib.SMTP(SMTP_SERVER, 587)
        server.starttls()
        server.login(email, password)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"❌ SMTP Error para {email}: {e}")
        return False

def responder_con_gemini(prompt_sistema, mensaje):
    """Genera respuesta usando Gemini SDK"""
    if not GEMINI_API_KEY:
        logger.error("❌ GEMINI_API_KEY no configurada")
        return "Lo siento, el servicio de IA no está disponible. Contacta al 938 120 6643."
    
    try:
        full_prompt = f"{prompt_sistema}\n\nCliente: {mensaje}\n\nAsistente:"
        response = model.generate_content(full_prompt)
        return response.text
    except Exception as e:
        logger.error(f"❌ Error en Gemini: {e}")
        return "Lo siento, estoy teniendo problemas técnicos. Contacta al 938 120 6643."

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
        logger.info(f"✅ Respuesta enviada a {para} desde {email_from}")
        return True
    except Exception as e:
        logger.error(f"❌ Error enviando desde {email_from}: {e}")
        return False

def leer_y_responder_cuenta(cuenta_correo, password, perfil):
    if not cuenta_correo or not password:
        logger.warning(f"⚠️ Credenciales incompletas para {perfil}")
        return
    
    try:
        logger.info(f"📡 {perfil} conectando a IMAP...")
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(cuenta_correo, password)
        mail.select('INBOX')
        
        result, data = mail.search(None, 'UNSEEN')
        correos_ids = data[0].split()
        
        if not correos_ids:
            logger.info(f"📭 No hay correos nuevos para {perfil}")
            mail.close()
            mail.logout()
            return
        
        logger.info(f"📧 {len(correos_ids)} correos nuevos para {perfil}")
        
        for email_id in correos_ids:
            logger.info(f"📥 Procesando correo ID: {email_id}")
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
            
            logger.info(f"📧 De: {remitente}")
            logger.info(f"📧 Asunto: {asunto}")
            logger.info(f"📝 Cuerpo: {cuerpo[:100]}...")
            
            if perfil == "Orion":
                prompt = PROMPT_ORION
            else:
                prompt = PROMPT_LUCIA
            
            logger.info("🤖 Generando respuesta con Gemini...")
            respuesta = responder_con_gemini(prompt, cuerpo)
            logger.info(f"💬 Respuesta generada: {respuesta[:100]}...")
            
            enviar_respuesta(remitente, asunto, respuesta, cuenta_correo, password)
            
            mail.store(email_id, '+FLAGS', '\\Seen')
            logger.info(f"✅ Respondido y marcado como leído")
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"❌ Error en {perfil}: {e}")

def procesar_todos_los_correos():
    logger.info("📬 Procesando todas las cuentas...")
    if EMAIL_CONTACTO and PASS_CONTACTO:
        leer_y_responder_cuenta(EMAIL_CONTACTO, PASS_CONTACTO, "Orion")
    if EMAIL_VENTAS and PASS_VENTAS:
        leer_y_responder_cuenta(EMAIL_VENTAS, PASS_VENTAS, "Lucía")
    logger.info("📬 Procesamiento completado")

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("🚀 CORELLA MULTI - Asistente de Correo (Gemini SDK)")
    print("=" * 60)
    print(f"📧 Orion 🔧: {EMAIL_CONTACTO}")
    print(f"📧 Lucía 💬: {EMAIL_VENTAS}")
    print(f"📡 IMAP: {IMAP_SERVER}")
    print(f"📡 SMTP: {SMTP_SERVER}")
    print(f"🤖 IA: Gemini 1.5 Flash")
    print("=" * 60)
    
    # Activar escudo para Render
    blindar_agente_en_render()
    
    print("\n🔍 Verificando conexiones...")
    todas_ok = True
    
    print(f"\n📧 Probando Orion (contacto@satecnetwork.com)...")
    if EMAIL_CONTACTO and PASS_CONTACTO:
        if test_imap(EMAIL_CONTACTO, PASS_CONTACTO) and test_smtp(EMAIL_CONTACTO, PASS_CONTACTO):
            print("✅ Orion - Conexiones OK")
        else:
            print("❌ Orion - Falló conexión")
            todas_ok = False
    else:
        print("⚠️ Orion - Sin credenciales")
    
    print(f"\n📧 Probando Lucía (ventas@satecnetwork.com)...")
    if EMAIL_VENTAS and PASS_VENTAS:
        if test_imap(EMAIL_VENTAS, PASS_VENTAS) and test_smtp(EMAIL_VENTAS, PASS_VENTAS):
            print("✅ Lucía - Conexiones OK")
        else:
            print("❌ Lucía - Falló conexión")
            todas_ok = False
    else:
        print("⚠️ Lucía - Sin credenciales")
    
    if todas_ok and GEMINI_API_KEY:
        print("\n✅ Conexiones exitosas. Iniciando monitoreo...")
        print("⏱️  Revisando cada 30 segundos.\n")
        
        procesar_todos_los_correos()
        
        while True:
            try:
                time.sleep(30)
                procesar_todos_los_correos()
            except KeyboardInterrupt:
                print("\n🛑 Corella Multi detenido")
                break
            except Exception as e:
                logger.error(f"❌ Error inesperado: {e}")
                time.sleep(10)
    else:
        print("\n⚠️ No se iniciará el monitoreo por fallas en conexiones.")
        if not GEMINI_API_KEY:
            print("   ❌ GEMINI_API_KEY no configurada")
