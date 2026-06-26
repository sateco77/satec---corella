#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
SOPORTE WORKER - Procesa correos de soporte para ORION (IA)
Lee correos desde contacto@satecnetwork.com y crea tareas para ORION
Credenciales desde variables de entorno (Render)
"""

import os
import imaplib
import smtplib
import mysql.connector
import json
import time
import ssl
import logging
import re
from email.mime.text import MIMEText
from datetime import datetime

# ============================================================
# CONFIGURACIÓN DESDE VARIABLES DE ENTORNO
# ============================================================

# Base de datos
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME', 'u416165369_corella_crm')

# Email de soporte
EMAIL_USER = os.environ.get('EMAIL_USER', 'contacto@satecnetwork.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))

# ID del agente ORION (Soporte)
AGENTE_ORION_ID = int(os.environ.get('AGENTE_ORION_ID', 55))

# Intervalo de revisión (minutos)
INTERVALO_MINUTOS = int(os.environ.get('INTERVALO_MINUTOS', 5))

# ============================================================
# VALIDACIÓN DE CONFIGURACIÓN
# ============================================================

if not all([DB_HOST, DB_USER, DB_PASSWORD, EMAIL_PASSWORD]):
    print("❌ ERROR: Faltan variables de entorno. Configura:")
    print("   DB_HOST, DB_USER, DB_PASSWORD, EMAIL_PASSWORD")
    exit(1)

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
# CONEXIÓN IMAP
# ============================================================

def conectar_imap():
    """Conecta al servidor IMAP de soporte"""
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

# ============================================================
# DETECTAR PALABRAS CLAVE DE SOPORTE
# ============================================================

def es_caso_soporte(texto):
    """Detecta si el correo es un caso de soporte técnico"""
    texto_lower = texto.lower()
    
    keywords_soporte = [
        'falla', 'error', 'problema', 'no funciona', 'avería', 'bug',
        'no enciende', 'pantalla', 'conexión', 'red', 'instalación',
        'configuración', 'cámara', 'gps', 'tracker', 'chip taxi', 'acceso',
        'biometría', 'huella', 'lector', 'alarma', 'sensor'
    ]
    
    for keyword in keywords_soporte:
        if keyword in texto_lower:
            return True
    return False

# ============================================================
# PROCESAR CORREOS
# ============================================================

def procesar_correos_soporte():
    """Procesa correos no leídos y crea tareas para ORION"""
    mail = conectar_imap()
    if not mail:
        return
    
    try:
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        
        if not email_ids:
            logger.info("📭 No hay correos nuevos")
            mail.close()
            mail.logout()
            return
        
        logger.info(f"📧 {len(email_ids)} correos nuevos de soporte")
        
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
                
                texto_completo = f"{asunto} {cuerpo}"
                
                # Verificar si es caso de soporte
                if not es_caso_soporte(texto_completo):
                    logger.info(f"⏭️  No es caso de soporte: {asunto[:30]}...")
                    mail.store(email_id, '+FLAGS', '\\Seen')
                    continue
                
                # Crear tarea para ORION
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tareas (texto, fecha_limite, asignada_por, asignada_a, fuente)
                    VALUES (%s, DATE_ADD(CURDATE(), INTERVAL 1 DAY), %s, %s, 'correo_soporte')
                """, (
                    f"🔧 SOPORTE: {remitente} - {asunto[:80]}...",
                    1,  # asignada_por (gerente)
                    AGENTE_ORION_ID
                ))
                conn.commit()
                tarea_id = cursor.lastrowid
                cursor.close()
                conn.close()
                
                logger.info(f"📋 Tarea de soporte creada (ID: {tarea_id}) para ORION")
                
                # Marcar como leído
                mail.store(email_id, '+FLAGS', '\\Seen')
                
            except Exception as e:
                logger.error(f"❌ Error procesando correo: {e}")
                continue
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"❌ Error procesando correos: {e}")

# ============================================================
# ACTUALIZAR ESTADO DE ORION
# ============================================================

def actualizar_estado_orion(estado):
    """Actualiza el estado de ORION en la DB"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agentes_config 
            SET estado = %s, ultima_conexion = NOW() 
            WHERE agente_id = %s AND canal = 'email_soporte'
        """, (estado, AGENTE_ORION_ID))
        conn.commit()
        cursor.close()
        conn.close()
        logger.info(f"📊 Estado de ORION actualizado: {estado}")
    except Exception as e:
        logger.error(f"❌ Error actualizando estado: {e}")

# ============================================================
# ENVIAR RESPUESTA (Opcional)
# ============================================================

def enviar_respuesta(para, asunto_original, respuesta):
    """Envía respuesta por correo (cuando ORION genera una respuesta)"""
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
    except Exception as e:
        logger.error(f"❌ Error enviando respuesta: {e}")

# ============================================================
# BUCLE PRINCIPAL
# ============================================================

def main():
    print("=" * 60)
    print("🔧 SOPORTE WORKER - ORION (IA)")
    print("=" * 60)
    print(f"📧 Email: {EMAIL_USER}")
    print(f"📡 IMAP: {IMAP_SERVER}")
    print(f"🤖 Agente: ORION (ID: {AGENTE_ORION_ID})")
    print(f"⏱️  Intervalo: {INTERVALO_MINUTOS} minutos")
    print("=" * 60)
    
    # Actualizar estado inicial
    actualizar_estado_orion('online')
    
    while True:
        try:
            logger.info("🔄 Ciclo de revisión iniciado")
            procesar_correos_soporte()
            
            logger.info(f"⏱️  Esperando {INTERVALO_MINUTOS} minutos...")
            time.sleep(INTERVALO_MINUTOS * 60)
            
        except KeyboardInterrupt:
            logger.info("🛑 Worker detenido")
            actualizar_estado_orion('offline')
            break
        except Exception as e:
            logger.error(f"❌ Error en ciclo principal: {e}")
            actualizar_estado_orion('error')
            time.sleep(60)

if __name__ == '__main__':
    main()
