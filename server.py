#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA para SATEC NETWORK
Con carga de entrenamiento local + Groq API
"""

import os
import json
import random
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# CARGA DEL ARCHIVO DE ENTRENAMIENTO
# ============================================================

def cargar_entrenamiento():
    """Carga el archivo de entrenamiento JSON"""
    rutas_posibles = [
        "entrenamientos/corella_entrenamiento_completo.json",
        "entrenamientos/entrenamiento.json",
        "entrenamiento.json",
        "../entrenamientos/entrenamiento.json",
        "entrenamiento_limpio.json"
    ]
    
    for ruta in rutas_posibles:
        if os.path.exists(ruta):
            try:
                with open(ruta, 'r', encoding='utf-8') as f:
                    datos = json.load(f)
                    print(f"✅ Cargado entrenamiento: {ruta} ({len(datos)} ejemplos)")
                    return datos
            except Exception as e:
                print(f"⚠️ Error cargando {ruta}: {e}")
    
    print("⚠️ No se encontró archivo de entrenamiento. Usando modo básico.")
    return []

# Cargar entrenamiento al iniciar
ENTRENAMIENTO = cargar_entrenamiento()

# Crear índice de búsqueda rápido por palabras clave
indice_entrenamiento = {}
for ejemplo in ENTRENAMIENTO:
    try:
        pregunta = ejemplo['messages'][1]['content'].lower()
        respuesta = ejemplo['messages'][2]['content']
        # Palabras clave de la pregunta
        palabras = set(pregunta.split())
        for palabra in palabras:
            if len(palabra) > 3:  # Ignorar palabras muy cortas
                if palabra not in indice_entrenamiento:
                    indice_entrenamiento[palabra] = []
                indice_entrenamiento[palabra].append({
                    'pregunta': pregunta,
                    'respuesta': respuesta,
                    'original': ejemplo
                })
    except:
        pass

print(f"📊 Índice de búsqueda creado: {len(indice_entrenamiento)} palabras clave")

# ============================================================
# CONFIGURACIÓN DE GROQ API
# ============================================================

GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

# Sistema prompt de SATEC (conocimiento de la empresa)
SISTEMA_PROMPT = """Eres CORELLA, el asistente virtual oficial de SATEC NETWORK.

🏢 SOBRE SATEC:
- Sistemas de Alta Tecnología & Seguridad
- Ubicación: Palenque, Chiapas
- Soporte 24/7: +52 938 120 6643

📡 SERVICIOS DE SATEC:

1. GPS TRACKER - Rastreo vehicular:
   • Básico Taxi: $100/mes (rastreo tiempo real, App PWA, historial 24h)
   • Full Logistics: $300/mes ($100 primer mes) (corte motor remoto, geocerca anti-robo, botón pánico, sensor velocidad)
   • Fleet Pro: $250/unidad (API integración, reportes combustible, soporte prioritario)

2. CHIP TAXI - App de taxis:
   • CHIP Lite: $45 base
   • CHIP Pro: $65 base  
   • CHIP Taxi: $50 base
   • Pagos: efectivo, tarjeta, transferencia o SATEC Wallet
   • Cobertura: Palenque, Chiapas (Parque Central, Zona Arqueológica, Aeropuerto)

3. CCTV VIDEO - Videovigilancia IA:
   • Residencial: $350/mes (2-4 cámaras, app móvil, detección personas)
   • Empresarial: $890/mes (8+ cámaras, IA avanzada, analíticas, respaldo 60 días)
   • 98% efectividad en detección de movimiento

4. ACCESS CONTROL - Control de acceso:
   • Biometría (huella, facial, iris) con 98.7% de precisión
   • QR dinámico integrado con SATEC Wallet
   • Protocolos: Wiegand, OSDP, API REST

🔑 CÓDIGO MAESTRO:
Cada cliente recibe un código único (ejemplo: ST-8829-GX) para autorizar descargas y movimientos de activos.

REGLAS DE RESPUESTA:
- Responde en español mexicano, usa "Inge" o "Ingeniero" de forma amigable
- Usa emojis según el servicio: 🚗 para GPS, 🚕 para CHIP TAXI, 🎥 para CCTV, 🔐 para Access Control
- Si no sabes algo, ofrece el soporte 24/7

Consulta del usuario: {consulta}
Respuesta de CORELLA:"""

# ============================================================
# FUNCIONES DE BÚSQUEDA EN ENTRENAMIENTO
# ============================================================

def buscar_en_entrenamiento(user_message):
    """Busca una respuesta similar en el entrenamiento"""
    if not ENTRENAMIENTO:
        return None
    
    user_lower = user_message.lower()
    user_palabras = set(user_lower.split())
    
    # Buscar por coincidencia de palabras clave
    puntuaciones = []
    for ejemplo in ENTRENAMIENTO:
        try:
            pregunta = ejemplo['messages'][1]['content'].lower()
            palabras_pregunta = set(pregunta.split())
            coincidencias = len(user_palabras & palabras_pregunta)
            if coincidencias > 0:
                puntuaciones.append((coincidencias, ejemplo))
        except:
            continue
    
    if puntuaciones:
        # Ordenar por mayor coincidencia
        puntuaciones.sort(reverse=True)
        mejor = puntuaciones[0][1]
        print(f"   📚 Respuesta encontrada en entrenamiento (coincidencia: {puntuaciones[0][0]} palabras)")
        return mejor['messages'][2]['content']
    
    return None

def consultar_groq(user_message):
    """Llama a Groq API y devuelve la respuesta"""
    if not GROQ_API_KEY:
        return None
    
    try:
        prompt_completo = SISTEMA_PROMPT.format(consulta=user_message)
        
        headers = {
            "Authorization": f"Bearer {GROQ_API_KEY}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": "llama3-8b-8192",
            "messages": [
                {"role": "system", "content": "Eres CORELLA, asistente de SATEC. Responde usando 'Inge' o 'Ingeniero'."},
                {"role": "user", "content": prompt_completo}
            ],
            "temperature": 0.3,
            "max_tokens": 500
        }
        
        response = requests.post(GROQ_URL, headers=headers, json=data, timeout=30)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"]
        else:
            print(f"Error Groq: {response.status_code}")
            return None
    except Exception as e:
        print(f"Error en consulta Groq: {e}")
        return None

# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>CORELLA SATEC</title>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1">
        <style>
            body { font-family: Arial, sans-serif; text-align: center; padding: 50px; background: #0a2e38; color: white; }
            h1 { color: #00a8ff; }
            .container { background: #1a1a2e; padding: 30px; border-radius: 15px; max-width: 600px; margin: 0 auto; }
            a { color: #00a8ff; text-decoration: none; }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>🛰️ CORELLA SATEC</h1>
            <p>Asistente IA para Sistemas de Alta Tecnología & Seguridad</p>
            <p>✅ Servidor funcionando correctamente</p>
            <p>📡 Servicios: GPS Tracker | CHIP TAXI | CCTV | Access Control</p>
            <p>📞 Soporte 24/7: <strong>+52 938 120 6643</strong></p>
            <hr>
            <p>🌐 <a href="/api/health">Estado del servicio (API Health)</a></p>
        </div>
    </body>
    </html>
    """

@app.route('/web/<path:path>')
def serve_web(path):
    return send_from_directory('web', path)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje, Inge'}), 400
        
        print(f"\n📨 Consulta: {user_message[:100]}")
        
        # PRIORIDAD 1: Buscar en entrenamiento local
        respuesta = buscar_en_entrenamiento(user_message)
        
        if respuesta:
            print(f"   ✅ Respuesta desde entrenamiento local")
            return jsonify({'response': respuesta, 'source': 'entrenamiento'})
        
        # PRIORIDAD 2: Consultar a Groq API
        print(f"   🌐 Consultando a Groq API...")
        respuesta = consultar_groq(user_message)
        
        if respuesta:
            print(f"   ✅ Respuesta desde Groq API")
            return jsonify({'response': respuesta, 'source': 'groq'})
        
        # PRIORIDAD 3: Respuesta por defecto
        respuesta = """📡 ¡Qué padre que preguntas, Inge! 📡

Para más información sobre **SATEC** (GPS Tracker, CHIP TAXI, CCTV o Access Control), llamanos al **+52 938 120 6643**.

¿Necesitas algo específico, Ingeniero? Estoy aquí para ayudarte con:
• 🚗 GPS Tracker y rastreo vehicular
• 🚕 CHIP TAXI y viajes
• 🎥 CCTV y videovigilancia
• 🔐 Control de acceso y biometría"""
        
        return jsonify({'response': respuesta, 'source': 'default'})
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC',
        'version': '2.0',
        'soporte': '+52 938 120 6643',
        'groq_configured': bool(GROQ_API_KEY),
        'entrenamiento_cargado': len(ENTRENAMIENTO) > 0,
        'ejemplos_entrenamiento': len(ENTRENAMIENTO)
    })

@app.route('/api/entrenamiento/stats', methods=['GET'])
def entrenamiento_stats():
    """Estadísticas del entrenamiento cargado"""
    return jsonify({
        'total_ejemplos': len(ENTRENAMIENTO),
        'palabras_clave': len(indice_entrenamiento),
        'archivo_cargado': bool(ENTRENAMIENTO)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA")
    print("=" * 60)
    print(f"🌐 Puerto: {PORT}")
    print(f"📚 Entrenamiento: {len(ENTRENAMIENTO)} ejemplos cargados")
    print(f"🔑 Groq API: {'Configurada' if GROQ_API_KEY else 'No configurada'}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
