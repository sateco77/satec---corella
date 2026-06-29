# server.py - SIN EMOJIS (COMPATIBLE CON RENDER)
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
# ESCUDO DE PROTECCION PARA RENDER
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
        print(f"[RENDER] No se pudo levantar el servidor falso: {e}")

def blindar_agente_en_render():
    hilo = threading.Thread(target=levantar_servidor_falso, daemon=True)
    hilo.start()
    print("[OK] Servidor falso en puerto 10000 activado")

# ============================================================
# CONFIGURACION DE CORREOS
# ============================================================

EMAIL_CONTACTO = os.getenv('EMAIL_USER_CONTACTO') or os.getenv('EMAIL_USER')
PASS_CONTACTO = os.getenv('EMAIL_PASS_CONTACTO') or os.getenv('EMAIL_PASS')

EMAIL_VENTAS = os.getenv('EMAIL_USER_VENTAS')
PASS_VENTAS = os.getenv('EMAIL_PASS_VENTAS')

IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.hostinger.com')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# ============================================================
# DIAGNOSTICO
# ============================================================
print("\n[DIAGNOSTICO DE CREDENCIALES]")
print(f"[CORREO] CONTACTO: {EMAIL_CONTACTO}")
print(f"[CORREO] VENTAS: {EMAIL_VENTAS}")
print(f"[GEMINI] API_KEY: {'CONFIGURADA' if GEMINI_API_KEY else 'VACIA'}")
print("=" * 60)

# ============================================================
# PERFILES Y PROMPTS
# ============================================================

PROMPT_ORION = """
Eres Orion, especialista en soporte tecnico de SATEC Network.
Atiendes el correo contacto@satecnetwork.com.

Tu personalidad:
- Tecnico, resolutivo y paciente
- Te enfocas en solucionar problemas
- Das instrucciones claras y paso a paso

SATEC ofrece soporte para:
1. GPS: Rastreo satelital, geocercas, corte de motor, localizacion de flotas.
2. CCTV: Camaras de videovigilancia, grabacion, monitoreo perimetral, IA.
3. Control de Acceso: Biometria, huella digital, QR, tarjetas, lectores.
4. Chip Taxi: App para taxis, viajes, conductores.

Responde de forma clara y tecnica, pero amable.
Si es una cotizacion, deriva a ventas@satecnetwork.com.
Telefono: 938 120 6643.
"""

PROMPT_LUCIA = """
Eres Lucia, asesora comercial de SATEC Network.
Atiendes el correo ventas@satecnetwork.com.

Tu personalidad:
- Enfocada en cerrar ventas
- Conoces precios y promociones
- Proactiva y persuasiva

SATEC ofrece:
1. GPS: Desde $500/mes por vehiculo
2. CCTV: Paquetes desde $3,000 (4 camaras + DVR)
3. Control de Acceso: Desde $2,500 por punto de acceso
4. Chip Taxi: Plan desde $300/mes por unidad

Siempre ofrece soluciones y menciona promociones.
Si es un problema tecnico, deriva a soporte@satecnetwork.com.
Telefono: 938 120 6643.
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
        logger.error(f"[IMAP] Error para {email}: {e}")
        return False

def test_smtp(email, password):
    try:
        server = smtplib.SMTP(SMTP_SERVER, 587)
        server.starttls()
        server.login(email, password)
        server.quit()
        return True
    except Exception as e:
        logger.error(f"[SMTP] Error para {email}: {e}")
        return False

def responder_con_gemini(prompt_sistema, mensaje):
    if not GEMINI_API_KEY:
        logger.error("[GEMINI] API_KEY no configurada")
        return "Lo siento, el servicio de IA no esta disponible. Contacta al 938 120 6643."
    
    try:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent?key={GEMINI_API_KEY}"
        headers = {'Content-Type': 'application/json'}
        payload = {
            "contents": [{
                "parts": [{
                    "text": f"{prompt_sistema}\n\nCliente: {mensaje}\n\nAsistente:"
                }]
            }]
        }
        
        response = requests.post(url, json=payload, headers=headers)
        response_json = response.json()
        
        respuesta_texto = response_json['candidates'][0]['content']['parts'][0]['text']
        return respuesta_texto
    except Exception as e:
        logger.error(f"[GEMINI] Error: {e}")
        return "Lo siento, estoy teniendo problemas tecnicos. Contacta al 938 120 6643."

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
        logger.info(f"[RESPUESTA] Enviada a {para} desde {email_from}")
        return True
    except Exception as e:
        logger.error(f"[RESPUESTA] Error desde {email_from}: {e}")
        return False

def leer_y_responder_cuenta(cuenta_correo, password, perfil):
    if not cuenta_correo or not password:
        logger.warning(f"[ADVERTENCIA] Credenciales incompletas para {perfil}")
        return
    
    try:
        logger.info(f"[IMAP] {perfil} conectando...")
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993, ssl_context=context)
        mail.login(cuenta_correo, password)
        mail.select('INBOX')
        
        result, data = mail.search(None, 'UNSEEN')
        correos_ids = data[0].split()
        
        if not correos_ids:
            logger.info(f"[IMAP] No hay correos nuevos para {perfil}")
            mail.close()
            mail.logout()
            return
        
        logger.info(f"[IMAP] {len(correos_ids)} correos nuevos para {perfil}")
        
        for email_id in correos_ids:
            logger.info(f"[PROCESANDO] Correo ID: {email_id}")
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
            
            logger.info(f"[CORREO] De: {remitente}")
            logger.info(f"[CORREO] Asunto: {asunto}")
            logger.info(f"[CORREO] Cuerpo: {cuerpo[:100]}...")
            
            if perfil == "Orion":
                prompt = PROMPT_ORION
            else:
                prompt = PROMPT_LUCIA
            
            logger.info("[IA] Generando respuesta con Gemini...")
            respuesta = responder_con_gemini(prompt, cuerpo)
            logger.info(f"[IA] Respuesta generada: {respuesta[:100]}...")
            
            enviar_respuesta(remitente, asunto, respuesta, cuenta_correo, password)
            
            mail.store(email_id, '+FLAGS', '\\Seen')
            logger.info(f"[OK] Respondido y marcado como leido")
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"[ERROR] en {perfil}: {e}")

def procesar_todos_los_correos():
    logger.info("[PROCESANDO] Todas las cuentas...")
    if EMAIL_CONTACTO and PASS_CONTACTO:
        leer_y_responder_cuenta(EMAIL_CONTACTO, PASS_CONTACTO, "Orion")
    if EMAIL_VENTAS and PASS_VENTAS:
        leer_y_responder_cuenta(EMAIL_VENTAS, PASS_VENTAS, "Lucia")
    logger.info("[PROCESANDO] Completado")

# ============================================================
# PROGRAMA PRINCIPAL
# ============================================================
if __name__ == '__main__':
    print("=" * 60)
    print("CORELLA MULTI - Asistente de Correo (Gemini)")
    print("=" * 60)
    print(f"[CORREO] Orion: {EMAIL_CONTACTO}")
    print(f"[CORREO] Lucia: {EMAIL_VENTAS}")
    print(f"[IMAP] Servidor: {IMAP_SERVER}")
    print(f"[SMTP] Servidor: {SMTP_SERVER}")
    print("[IA] Gemini 1.5 Flash")
    print("=" * 60)
    
    # Activar escudo para Render
    blindar_agente_en_render()
    
    print("\n[VERIFICANDO] Conexiones...")
    todas_ok = True
    
    print(f"\n[TEST] Orion (contacto@satecnetwork.com)...")
    if EMAIL_CONTACTO and PASS_CONTACTO:
        if test_imap(EMAIL_CONTACTO, PASS_CONTACTO) and test_smtp(EMAIL_CONTACTO, PASS_CONTACTO):
            print("[OK] Orion - Conexiones OK")
        else:
            print("[ERROR] Orion - Fallo conexion")
            todas_ok = False
    else:
        print("[ADVERTENCIA] Orion - Sin credenciales")
    
    print(f"\n[TEST] Lucia (ventas@satecnetwork.com)...")
    if EMAIL_VENTAS and PASS_VENTAS:
        if test_imap(EMAIL_VENTAS, PASS_VENTAS) and test_smtp(EMAIL_VENTAS, PASS_VENTAS):
            print("[OK] Lucia - Conexiones OK")
        else:
            print("[ERROR] Lucia - Fallo conexion")
            todas_ok = False
    else:
        print("[ADVERTENCIA] Lucia - Sin credenciales")
    
    if todas_ok:
        print("\n[OK] Conexiones exitosas. Iniciando monitoreo...")
        print("[TIMER] Revisando cada 30 segundos.\n")
        
        procesar_todos_los_correos()
        
        while True:
            try:
                time.sleep(30)
                procesar_todos_los_correos()
            except KeyboardInterrupt:
                print("\n[DETENIDO] Corella Multi detenido")
                break
            except Exception as e:
                logger.error(f"[ERROR] Inesperado: {e}")
                time.sleep(10)
    else:
        print("\n[ERROR] No se iniciara el monitoreo por fallas en conexiones.")
