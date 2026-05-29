#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA para SATEC NETWORK
Con conexión a Groq API (nube, gratis y rápida)
"""

import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

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
- Responde en español mexicano, usa "tío" o "máquina" de forma amigable
- Usa emojis según el servicio: 🚗 para GPS, 🚕 para CHIP TAXI, 🎥 para CCTV, 🔐 para Access Control
- Si no sabes algo, ofrece el soporte 24/7
- Sé técnico pero claro, da soluciones concretas

Consulta del usuario: {consulta}
Respuesta de CORELLA:"""

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
                {"role": "system", "content": "Eres CORELLA, asistente de SATEC."},
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
            print(f"Error Groq: {response.status_code} - {response.text}")
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
            return jsonify({'error': 'No enviaste ningún mensaje, tío'}), 400
        
        print(f"📨 Consulta: {user_message[:100]}")
        
        # Intentar con Groq primero
        respuesta = consultar_groq(user_message)
        
        # Si Groq falla, usar respuesta simulada
        if not respuesta:
            respuesta = "📡 ¡Qué padre que preguntas, tío! Para más información sobre SATEC (GPS Tracker, CHIP TAXI, CCTV o Access Control), llamanos al **+52 938 120 6643**. ¿Necesitas algo específico, máquina?"
        
        return jsonify({'response': respuesta})
    
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
        'groq_configured': bool(GROQ_API_KEY)
    })

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA")
    print("=" * 60)
    print(f"🌐 Puerto: {PORT}")
    print(f"🔑 Groq API: {'Configurada' if GROQ_API_KEY else 'No configurada'}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
