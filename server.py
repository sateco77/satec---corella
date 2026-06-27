#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - SISTEMA DE AGENTES IA (3 Roles)
- ÁGATA: Marketing (RSS + LinkedIn)
- LUCÍA: Ventas (Correo entrante)
- ORION: Soporte (Correo entrante + Tickets)
"""

import os
import sys
import time
import re
import json
import logging
import schedule
import requests
import feedparser
import imaplib
import smtplib
import email
import ssl
import mysql.connector
from email.mime.text import MIMEText
from datetime import datetime
from dotenv import load_dotenv

# =====================================================
# CONFIGURACIÓN
# =====================================================

# Cargar .env
env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'shared', '.env')
load_dotenv(env_path)

# Configurar logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)

# =====================================================
# CONFIGURACIÓN DE ROLES
# =====================================================

ROLES = {
    'agata': {
        'nombre': 'Ágata (IA)',
        'rol': 'MARKETING',
        'emoji': '📊',
        'descripcion': 'Lee RSS del blog, genera y publica en LinkedIn',
        'rss_feed': 'https://fetchrss.com/feed/1vwMhuGJz7Vq1vwMr1DC04bC.rss',
        'modelo_llama': 'erwan2/DeepSeek-R1-Distill-Qwen-7B',
        'horarios': ['09:00', '14:00', '21:00']
    },
    'lucia': {
        'nombre': 'Lucía (IA)',
        'rol': 'VENTAS',
        'emoji': '💬',
        'descripcion': 'Responde correos de ventas, cotiza y negocia',
        'email': 'ventas@satecnetwork.com',
        'password': '7V3nt@s@77tec',
        'imap_server': 'imap.hostinger.com',
        'smtp_server': 'smtp.hostinger.com'
    },
    'orion': {
        'nombre': 'Orion (IA)',
        'rol': 'SOPORTE',
        'emoji': '🔧',
        'descripcion': 'Responde correos de soporte, crea tickets',
        'email': 'contacto@satecnetwork.com',
        'password': '7Cont@77tec',
        'imap_server': 'imap.hostinger.com',
        'smtp_server': 'smtp.hostinger.com'
    }
}

# =====================================================
# ÁGATA - MARKETING (RSS + LinkedIn)
# =====================================================

class AgenteAgata:
    """Agente de Marketing - RSS a LinkedIn"""
    
    def __init__(self):
        self.nombre = ROLES['agata']['nombre']
        self.rss_feed = ROLES['agata']['rss_feed']
        self.modelo = ROLES['agata']['modelo_llama']
        self.archivo_vistos = "posts_publicados.txt"
        self.archivo_cola = "cola_posts.txt"
        
        # Credenciales LinkedIn
        self.linkedin_token = os.getenv('LINKEDIN_ACCESS_TOKEN')
        self.linkedin_person_urn = os.getenv('LINKEDIN_PERSON_URN')
        
        if not self.linkedin_token or not self.linkedin_person_urn:
            logger.error("❌ Faltan credenciales de LinkedIn en .env")
            sys.exit(1)
        
        self._asegurar_archivos()
    
    def _asegurar_archivos(self):
        """Crea los archivos si no existen"""
        for archivo in [self.archivo_vistos, self.archivo_cola]:
            if not os.path.exists(archivo):
                with open(archivo, 'w', encoding='utf-8') as f:
                    f.write('')
    
    def _limpiar_html(self, texto):
        """Limpia HTML y basura de FetchRSS"""
        if not texto:
            return ""
        texto_limpio = re.sub(r'<[^>]+>', ' ', texto)
        texto_limpio = re.sub(r'\(Feed generated with .*?FetchRSS.*?\)', '', texto_limpio)
        texto_limpio = re.sub(r'\(Feed gener.*?\)', '', texto_limpio)
        return ' '.join(texto_limpio.split())
    
    def _cargar_cola(self):
        """Carga la cola de posts pendientes"""
        try:
            with open(self.archivo_cola, 'r', encoding='utf-8') as f:
                return [line.strip() for line in f.readlines() if line.strip()]
        except:
            return []
    
    def _guardar_cola(self, cola):
        """Guarda la cola de posts"""
        with open(self.archivo_cola, 'w', encoding='utf-8') as f:
            for item in cola:
                if item.strip():
                    f.write(f"{item}\n")
    
    def _agregar_a_cola(self, link, titulo, contenido):
        """Agrega un post a la cola"""
        titulo_limpio = self._limpiar_html(titulo)
        contenido_limpio = self._limpiar_html(contenido)
        entrada = f"{link}||{titulo_limpio}||{contenido_limpio}"
        
        cola = self._cargar_cola()
        if entrada in cola:
            return
        
        # Verificar si ya fue publicado
        if os.path.exists(self.archivo_vistos):
            with open(self.archivo_vistos, 'r', encoding='utf-8') as f:
                if link in f.read():
                    return
        
        cola.append(entrada)
        self._guardar_cola(cola)
        logger.info(f"📝 Agregado a cola: {titulo_limpio[:40]}...")
    
    def _obtener_siguiente_de_cola(self):
        """Obtiene y elimina el primer post de la cola"""
        cola = self._cargar_cola()
        if not cola:
            return None
        
        primero = cola.pop(0)
        self._guardar_cola(cola)
        
        try:
            partes = primero.split('||', 2)
            if len(partes) == 3:
                return partes[0], partes[1], partes[2]
        except:
            pass
        return None
    
    def leer_rss(self):
        """Lee el feed RSS y carga posts nuevos"""
        logger.info(f"📡 Leyendo RSS: {self.rss_feed}")
        try:
            feed = feedparser.parse(self.rss_feed)
        except Exception as e:
            logger.error(f"❌ Error leyendo RSS: {e}")
            return
        
        with open(self.archivo_vistos, 'r', encoding='utf-8') as f:
            vistos = set(f.read().splitlines())
        
        for entry in feed.entries:
            link = entry.get('link', '')
            titulo = entry.get('title', '')
            descripcion = entry.get('description', '')
            
            if link and link not in vistos:
                contenido = f"{titulo}\n\n{descripcion}"
                self._agregar_a_cola(link, titulo, contenido)
        
        logger.info(f"📊 Posts en cola: {len(self._cargar_cola())}")
    
    def _generar_con_llama(self, prompt):
        """Genera texto usando Llama"""
        try:
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.8, "max_tokens": 800}
                },
                timeout=180
            )
            if response.status_code == 200:
                return response.json().get('response', '').strip()
        except Exception as e:
            logger.error(f"❌ Error en Llama: {e}")
        return None
    
    def _generar_post(self, texto_original, hora):
        """Genera post según la hora del día"""
        estilos = {
            '09:00': {
                'nombre': 'matutino',
                'tono': 'Energético, motivador, de "buenos días"',
                'enfoque': 'Comienza tu día con planes increíbles'
            },
            '14:00': {
                'nombre': 'inspirador',
                'tono': 'Reflexivo, inspirador, de "pausa para soñar"',
                'enfoque': 'Escápate de la rutina, planea tu próxima aventura'
            },
            '21:00': {
                'nombre': 'nocturno',
                'tono': 'Cálido, acogedor, de "buenas noches"',
                'enfoque': 'Relax, confort, el descanso que mereces'
            }
        }
        
        estilo = estilos.get(hora, estilos['09:00'])
        
        prompt = f"""Eres ÁGATA, la estratega de contenido de SATEC NETWORK.

CREA UN POST PARA LINKEDIN ({hora}):
✅ Tono: {estilo['tono']}
✅ Enfoque: {estilo['enfoque']}
✅ Longitud: 150-250 palabras
✅ Hashtags: 5 mezclando #SATEC #Tecnología #Seguridad #Innovación #IA

INFORMACIÓN ORIGINAL:
{texto_original}

POST {estilo['nombre'].upper()}:
"""
        return self._generar_con_llama(prompt)
    
    def _publicar_en_linkedin(self, texto):
        """Publica en LinkedIn"""
        url = "https://api.linkedin.com/v2/ugcPosts"
        headers = {
            'Authorization': f'Bearer {self.linkedin_token}',
            'Content-Type': 'application/json',
            'X-Restli-Protocol-Version': '2.0.0'
        }
        
        payload = {
            "author": self.linkedin_person_urn,
            "lifecycleState": "PUBLISHED",
            "specificContent": {
                "com.linkedin.ugc.ShareContent": {
                    "shareCommentary": {"text": texto[:2000]},
                    "shareMediaCategory": "NONE"
                }
            },
            "visibility": {"com.linkedin.ugc.MemberNetworkVisibility": "PUBLIC"}
        }
        
        try:
            response = requests.post(url, headers=headers, json=payload)
            if response.status_code in [201, 422]:
                return True
            logger.error(f"❌ Error LinkedIn: {response.status_code}")
        except Exception as e:
            logger.error(f"❌ Excepción LinkedIn: {e}")
        return False
    
    def _ya_publico_hoy(self):
        """Verifica si ya se publicaron 3 posts hoy"""
        archivo = f"publicaciones_{datetime.now().strftime('%Y-%m-%d')}.txt"
        if not os.path.exists(archivo):
            return False
        try:
            with open(archivo, 'r', encoding='utf-8') as f:
                return len(f.read().splitlines()) >= 3
        except:
            return False
    
    def _registrar_publicacion(self, hora):
        """Registra una publicación"""
        archivo = f"publicaciones_{datetime.now().strftime('%Y-%m-%d')}.txt"
        with open(archivo, 'a', encoding='utf-8') as f:
            f.write(f"{hora}\n")
    
    def publicar(self, hora):
        """Publica un post en LinkedIn a la hora indicada"""
        logger.info(f"🌅 Publicando post de {hora}")
        
        if self._ya_publico_hoy():
            logger.info("⏸️ Ya se publicaron 3 posts hoy")
            return
        
        siguiente = self._obtener_siguiente_de_cola()
        if not siguiente:
            logger.info("📭 No hay posts en cola, leyendo RSS...")
            self.leer_rss()
            siguiente = self._obtener_siguiente_de_cola()
            if not siguiente:
                return
        
        link, titulo, contenido = siguiente
        logger.info(f"📝 Procesando: {titulo[:50]}...")
        
        post = self._generar_post(contenido, hora)
        if post and self._publicar_en_linkedin(post):
            with open(self.archivo_vistos, 'a', encoding='utf-8') as f:
                f.write(link + '\n')
            self._registrar_publicacion(hora)
            logger.info(f"✅ Post de {hora} publicado")

# =====================================================
# LUCÍA - VENTAS (Correo entrante)
# =====================================================

class AgenteLucia:
    """Agente de Ventas - Responde correos entrantes"""
    
    def __init__(self):
        self.nombre = ROLES['lucia']['nombre']
        self.email = ROLES['lucia']['email']
        self.password = ROLES['lucia']['password']
        self.imap_server = ROLES['lucia']['imap_server']
        self.smtp_server = ROLES['lucia']['smtp_server']
        self.modelo = 'llama3.2:latest'
        self.db_config = {
            'host': os.getenv('DB_HOST', 'peru-clam-144838.hostingersite.com'),
            'user': os.getenv('DB_USER', 'u416165369_corella75'),
            'password': os.getenv('DB_PASSWORD', '7Crm7408'),
            'database': os.getenv('DB_NAME', 'u416165369_corella_crm')
        }
    
    def _get_prompt_ventas(self, mensaje):
        return f"""Eres LUCÍA (IA), asesora de VENTAS de SATEC.

💬 TU ROL: Vender servicios de SATEC

📡 SERVICIOS:
1. GPS TRACKER: Básico Taxi ($100/mes) | Full Logistics ($300/mes) | Fleet Pro ($250/unidad)
2. CHIP TAXI: CHIP Lite ($45) | CHIP Pro ($65) | CHIP Taxi ($50)
3. CCTV VIDEO: Residencial ($350/mes) | Empresarial ($890/mes)
4. ACCESS CONTROL: Biometría, QR dinámico

🎯 REGLAS:
- Enfatiza beneficios y ahorros
- Ofrece promociones
- Pregunta necesidades del cliente
- Termina con pregunta

Cliente: {mensaje}
Respuesta de LUCÍA (Ventas):"""
    
    def _conectar_imap(self):
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(self.imap_server, 993, ssl_context=context)
            mail.login(self.email, self.password)
            mail.select('INBOX')
            return mail
        except Exception as e:
            logger.error(f"❌ IMAP {self.nombre}: {e}")
            return None
    
    def _enviar_respuesta(self, para, asunto, mensaje):
        try:
            msg = MIMEText(mensaje, 'plain', 'utf-8')
            msg['Subject'] = f"Re: {asunto}"
            msg['From'] = self.email
            msg['To'] = para
            
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(self.smtp_server, 465, context=context)
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"❌ SMTP {self.nombre}: {e}")
            return False
    
    def _generar_respuesta(self, mensaje):
        try:
            prompt = self._get_prompt_ventas(mensaje)
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.3}
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            logger.error(f"❌ Llama {self.nombre}: {e}")
        return "📊 ¡Gracias por contactar a SATEC! Soy Lucía, tu asesora de ventas. ¿Te gustaría recibir una cotización personalizada? 🚀"
    
    def procesar(self):
        """Procesa correos de ventas"""
        logger.info(f"📡 {self.nombre} - Leyendo correos...")
        mail = self._conectar_imap()
        if not mail:
            return
        
        try:
            result, data = mail.search(None, 'UNSEEN')
            ids = data[0].split()
            logger.info(f"📧 {self.nombre} - {len(ids)} correos nuevos")
            
            for email_id in ids:
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
                    
                    logger.info(f"📥 {self.nombre} - De: {remitente} - {asunto[:50]}")
                    
                    respuesta = self._generar_respuesta(cuerpo)
                    
                    if self._enviar_respuesta(remitente, asunto, respuesta):
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        logger.info(f"✉️ {self.nombre} - Respondido a {remitente}")
                    
                except Exception as e:
                    logger.error(f"❌ {self.nombre} - Error en correo: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"❌ {self.nombre} - Error general: {e}")

# =====================================================
# ORION - SOPORTE (Correo entrante + Tickets)
# =====================================================

class AgenteOrion:
    """Agente de Soporte - Responde correos y crea tickets"""
    
    def __init__(self):
        self.nombre = ROLES['orion']['nombre']
        self.email = ROLES['orion']['email']
        self.password = ROLES['orion']['password']
        self.imap_server = ROLES['orion']['imap_server']
        self.smtp_server = ROLES['orion']['smtp_server']
        self.modelo = 'llama3.2:latest'
        self.db_config = {
            'host': os.getenv('DB_HOST', 'peru-clam-144838.hostingersite.com'),
            'user': os.getenv('DB_USER', 'u416165369_corella75'),
            'password': os.getenv('DB_PASSWORD', '7Crm7408'),
            'database': os.getenv('DB_NAME', 'u416165369_corella_crm')
        }
    
    def _get_prompt_soporte(self, mensaje):
        return f"""Eres ORION (IA), técnico de SOPORTE de SATEC.

🔧 TU ROL: Resolver problemas técnicos

📡 EQUIPOS:
1. GPS TRACKER: Instalación, configuración, fallas
2. CHIP TAXI: Integración, pagos, geolocalización
3. CCTV VIDEO: Instalación, configuración de IA
4. ACCESS CONTROL: Biometría, integración

🎯 REGLAS:
- Diagnostica paso a paso
- Da instrucciones claras
- Escala si es necesario

Cliente: {mensaje}
Respuesta de ORION (Soporte):"""
    
    def _conectar_imap(self):
        try:
            context = ssl.create_default_context()
            mail = imaplib.IMAP4_SSL(self.imap_server, 993, ssl_context=context)
            mail.login(self.email, self.password)
            mail.select('INBOX')
            return mail
        except Exception as e:
            logger.error(f"❌ IMAP {self.nombre}: {e}")
            return None
    
    def _enviar_respuesta(self, para, asunto, mensaje):
        try:
            msg = MIMEText(mensaje, 'plain', 'utf-8')
            msg['Subject'] = f"Re: {asunto}"
            msg['From'] = self.email
            msg['To'] = para
            
            context = ssl.create_default_context()
            server = smtplib.SMTP_SSL(self.smtp_server, 465, context=context)
            server.login(self.email, self.password)
            server.send_message(msg)
            server.quit()
            return True
        except Exception as e:
            logger.error(f"❌ SMTP {self.nombre}: {e}")
            return False
    
    def _generar_respuesta(self, mensaje):
        try:
            prompt = self._get_prompt_soporte(mensaje)
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.modelo,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.2}
                },
                timeout=60
            )
            if response.status_code == 200:
                return response.json().get('response', '')
        except Exception as e:
            logger.error(f"❌ Llama {self.nombre}: {e}")
        return "🔧 Soy Orion, tu técnico de soporte. ¿Puedes darme más detalles sobre el problema? 💻"
    
    def _crear_ticket(self, remitente, asunto):
        """Crea un ticket en la base de datos"""
        try:
            conn = mysql.connector.connect(**self.db_config)
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tareas (texto, fecha_limite, asignada_por, asignada_a, fuente)
                VALUES (%s, DATE_ADD(CURDATE(), INTERVAL 2 DAY), %s, %s, 'soporte')
            """, (f"Ticket de {remitente}: {asunto[:50]}", 1, 6))
            conn.commit()
            ticket_id = cursor.lastrowid
            cursor.close()
            conn.close()
            logger.info(f"📋 Ticket creado ID: {ticket_id}")
            return ticket_id
        except Exception as e:
            logger.error(f"❌ Error creando ticket: {e}")
            return None
    
    def procesar(self):
        """Procesa correos de soporte"""
        logger.info(f"📡 {self.nombre} - Leyendo correos...")
        mail = self._conectar_imap()
        if not mail:
            return
        
        try:
            result, data = mail.search(None, 'UNSEEN')
            ids = data[0].split()
            logger.info(f"📧 {self.nombre} - {len(ids)} correos nuevos")
            
            for email_id in ids:
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
                    
                    logger.info(f"📥 {self.nombre} - De: {remitente} - {asunto[:50]}")
                    
                    # Crear ticket
                    self._crear_ticket(remitente, asunto)
                    
                    # Generar y enviar respuesta
                    respuesta = self._generar_respuesta(cuerpo)
                    
                    if self._enviar_respuesta(remitente, asunto, respuesta):
                        mail.store(email_id, '+FLAGS', '\\Seen')
                        logger.info(f"✉️ {self.nombre} - Respondido a {remitente}")
                    
                except Exception as e:
                    logger.error(f"❌ {self.nombre} - Error en correo: {e}")
                    continue
            
            mail.close()
            mail.logout()
            
        except Exception as e:
            logger.error(f"❌ {self.nombre} - Error general: {e}")

# =====================================================
# PROGRAMA PRINCIPAL
# =====================================================

if __name__ == '__main__':
    if len(sys.argv) < 2 or sys.argv[1] not in ROLES:
        print("=" * 60)
        print("🚀 CORELLA - SISTEMA DE AGENTES IA")
        print("=" * 60)
        print("Uso: python corella_agentes.py [agata|lucia|orion]")
        print("")
        print("📊 agata - Marketing (RSS → LinkedIn)")
        print("💬 lucia - Ventas (Correo entrante)")
        print("🔧 orion - Soporte (Correo entrante + Tickets)")
        print("=" * 60)
        sys.exit(1)
    
    rol = sys.argv[1]
    
    if rol == 'agata':
        agente = AgenteAgata()
        print("=" * 60)
        print("📊 ÁGATA - Marketing")
        print("=" * 60)
        print("⏰ Programando publicaciones:")
        print("   09:00 - Post matutino")
        print("   14:00 - Post inspirador")
        print("   21:00 - Post nocturno")
        print("=" * 60)
        
        # Leer RSS inicial
        agente.leer_rss()
        
        # Programar publicaciones
        schedule.every().day.at("09:00").do(lambda: agente.publicar("09:00"))
        schedule.every().day.at("14:00").do(lambda: agente.publicar("14:00"))
        schedule.every().day.at("21:00").do(lambda: agente.publicar("21:00"))
        
        while True:
            schedule.run_pending()
            time.sleep(60)
    
    elif rol == 'lucia':
        agente = AgenteLucia()
        print("=" * 60)
        print("💬 LUCÍA - Ventas")
        print("=" * 60)
        print(f"📧 Correo: {agente.email}")
        print("⏱️  Revisando correos cada 30 segundos...")
        print("=" * 60)
        
        while True:
            try:
                agente.procesar()
                time.sleep(30)
            except KeyboardInterrupt:
                print("\n🛑 Agente detenido")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                time.sleep(60)
    
    elif rol == 'orion':
        agente = AgenteOrion()
        print("=" * 60)
        print("🔧 ORION - Soporte")
        print("=" * 60)
        print(f"📧 Correo: {agente.email}")
        print("⏱️  Revisando correos cada 30 segundos...")
        print("=" * 60)
        
        while True:
            try:
                agente.procesar()
                time.sleep(30)
            except KeyboardInterrupt:
                print("\n🛑 Agente detenido")
                break
            except Exception as e:
                logger.error(f"❌ Error: {e}")
                time.sleep(60)
