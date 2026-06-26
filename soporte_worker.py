#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA EMAIL WORKER - Procesa correos y asigna tareas a agentes IA
Las credenciales se cargan desde variables de entorno (Render)
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

# Base de datos (desde variables de entorno)
DB_HOST = os.environ.get('DB_HOST')
DB_USER = os.environ.get('DB_USER')
DB_PASSWORD = os.environ.get('DB_PASSWORD')
DB_NAME = os.environ.get('DB_NAME', 'u416165369_corella_crm')

# Email (desde variables de entorno)
EMAIL_USER = os.environ.get('EMAIL_USER')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD')
IMAP_SERVER = os.environ.get('IMAP_SERVER', 'imap.hostinger.com')
SMTP_SERVER = os.environ.get('SMTP_SERVER', 'smtp.hostinger.com')
SMTP_PORT = int(os.environ.get('SMTP_PORT', 465))

# Intervalo de revisión (minutos)
INTERVALO_MINUTOS = int(os.environ.get('INTERVALO_MINUTOS', 5))

# ============================================================
# VALIDACIÓN DE CONFIGURACIÓN
# ============================================================

if not all([DB_HOST, DB_USER, DB_PASSWORD, EMAIL_USER, EMAIL_PASSWORD]):
    print("❌ ERROR: Faltan variables de entorno. Asegúrate de configurar:")
    print("   DB_HOST, DB_USER, DB_PASSWORD, EMAIL_USER, EMAIL_PASSWORD")
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
    """Retorna conexión a la base de datos usando variables de entorno"""
    return mysql.connector.connect(
        host=DB_HOST,
        user=DB_USER,
        password=DB_PASSWORD,
        database=DB_NAME
    )

# ============================================================
# OBTENER AGENTES CON EMAIL CONFIGURADO
# ============================================================

def get_agentes_email():
    """Obtiene agentes con configuración de email activa"""
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT 
            u.id,
            u.nombre,
            ac.credenciales,
            ac.canal,
            u.especialidades
        FROM agentes_config ac
        JOIN usuarios u ON ac.agente_id = u.id
        WHERE ac.canal IN ('email', 'email_soporte') 
        AND ac.activo = 1
    """)
    agentes = cursor.fetchall()
    cursor.close()
    conn.close()
    return agentes

# ============================================================
# FUNCIONES PRINCIPALES
# ============================================================

def detectar_especialidad(texto):
    """Detecta la especialidad basada en palabras clave"""
    texto_lower = texto.lower()
    
    keywords = {
        'gps': ['gps', 'rastreo', 'flota', 'geocerca', 'vehículo', 'tracking'],
        'cctv': ['cámara', 'video', 'vigilancia', 'cctv', 'movimiento'],
        'access': ['acceso', 'biometría', 'huella', 'qr', 'lector'],
        'chip_taxi': ['taxi', 'viaje', 'chip taxi', 'conductor']
    }
    
    for especialidad, palabras in keywords.items():
        for palabra in palabras:
            if palabra in texto_lower:
                return especialidad
    return None

def conectar_imap(credenciales):
    """Conecta al servidor IMAP usando credenciales del agente"""
    try:
        email_user = credenciales.get('email') or EMAIL_USER
        email_pass = credenciales.get('password') or EMAIL_PASSWORD
        imap_server = credenciales.get('imap_server', IMAP_SERVER)
        
        context = ssl.create_default_context()
        mail = imaplib.IMAP4_SSL(imap_server, 993, ssl_context=context)
        mail.login(email_user, email_pass)
        mail.select('INBOX')
        return mail
    except Exception as e:
        logger.error(f"❌ Error conectando IMAP: {e}")
        return None

def procesar_correos(agente_id, nombre, credenciales):
    """Procesa correos no leídos para un agente"""
    mail = conectar_imap(credenciales)
    if not mail:
        return
    
    try:
        result, data = mail.search(None, 'UNSEEN')
        email_ids = data[0].split()
        logger.info(f"📧 {len(email_ids)} correos nuevos para {nombre}")
        
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
                
                logger.info(f"📧 De: {remitente} | Asunto: {asunto[:50]}")
                
                # Crear tarea en la base de datos
                conn = get_db_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO tareas (texto, fecha_limite, asignada_por, asignada_a, fuente)
                    VALUES (%s, DATE_ADD(CURDATE(), INTERVAL 1 DAY), %s, %s, 'correo')
                """, (
                    f"Correo de {remitente}: {asunto[:50]}...",
                    1, agente_id
                ))
                conn.commit()
                tarea_id = cursor.lastrowid
                cursor.close()
                conn.close()
                
                logger.info(f"📋 Tarea creada (ID: {tarea_id}) para {nombre}")
                mail.store(email_id, '+FLAGS', '\\Seen')
                
            except Exception as e:
                logger.error(f"❌ Error procesando correo: {e}")
                continue
        
        mail.close()
        mail.logout()
        
    except Exception as e:
        logger.error(f"❌ Error procesando correos: {e}")

def actualizar_estado(agente_id, estado):
    """Actualiza el estado del agente en la DB"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE agentes_config 
            SET estado = %s, ultima_conexion = NOW() 
            WHERE agente_id = %s
        """, (estado, agente_id))
        conn.commit()
        cursor.close()
        conn.close()
    except Exception as e:
        logger.error(f"❌ Error actualizando estado: {e}")

# ============================================================
# BUCLE PRINCIPAL
# ============================================================

def main():
    logger.info("=" * 60)
    logger.info("🚀 CORELLA EMAIL WORKER")
    logger.info("=" * 60)
    logger.info(f"📧 Email: {EMAIL_USER}")
    logger.info(f"📡 IMAP: {IMAP_SERVER}")
    logger.info(f"⏱️  Intervalo: {INTERVALO_MINUTOS} minutos")
    logger.info("=" * 60)
    
    while True:
        try:
            agentes = get_agentes_email()
            logger.info(f"📋 {len(agentes)} agentes con email configurado")
            
            for agente in agentes:
                try:
                    agente_id = agente['id']
                    nombre = agente['nombre']
                    credenciales = json.loads(agente['credenciales'])
                    
                    actualizar_estado(agente_id, 'online')
                    procesar_correos(agente_id, nombre, credenciales)
                    
                except Exception as e:
                    logger.error(f"❌ Error procesando agente: {e}")
                    actualizar_estado(agente_id, 'error')
            
            logger.info(f"⏱️  Esperando {INTERVALO_MINUTOS} minutos...")
            time.sleep(INTERVALO_MINUTOS * 60)
            
        except KeyboardInterrupt:
            logger.info("🛑 Worker detenido")
            break
        except Exception as e:
            logger.error(f"❌ Error: {e}")
            time.sleep(60)

if __name__ == '__main__':
    main()
