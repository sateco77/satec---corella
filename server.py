#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA para SATEC NETWORK
Versión para Render (sin Ollama local)
"""

import os
import json
import requests
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# ============================================================
# SISTEMA PROMPT DE SATEC
# ============================================================

SISTEMA_PROMPT = """
Eres CORELLA, el asistente virtual oficial de SATEC NETWORK.

🏢 SOBRE SATEC:
- Sistemas de Alta Tecnología & Seguridad
- Ubicación: Palenque, Chiapas
- Soporte 24/7: +52 938 120 6643

📡 SERVICIOS DE SATEC:

1. GPS TRACKER - Rastreo vehicular:
   • Básico Taxi: $100/mes (rastreo tiempo real, App PWA)
   • Full Logistics: $300/mes ($100 primer mes) (corte motor remoto, geocerca anti-robo)
   • Fleet Pro: $250/unidad (API, reportes combustible)

2. CHIP TAXI - App de taxis:
   • CHIP Lite: $45 base
   • CHIP Pro: $65 base  
   • CHIP Taxi: $50 base

3. CCTV VIDEO - Videovigilancia IA:
   • Residencial: $350/mes (2-4 cámaras)
   • Empresarial: $890/mes (8+ cámaras, IA avanzada)

4. ACCESS CONTROL - Control de acceso:
   • Biometría (huella, facial, iris)
   • QR dinámico
   • Integración con SATEC GPS + CCTV

REGLAS:
- Responde en español mexicano, usa "tío" o "máquina"
- Usa emojis según el servicio
- Si no sabes algo, ofrece el soporte 24/7

Consulta del usuario: {consulta}
Respuesta de CORELLA:
"""

def generar_respuesta(user_message):
    """Genera respuesta simulada (funciona sin API externa)"""
    prompt_lower = user_message.lower()
    
    if "gps" in prompt_lower or "rastreo" in prompt_lower or "flota" in prompt_lower:
        return "🚗 ¡Ahí te va, tío! **SATEC GPS Tracker** ofrece el plan **Básico Taxi por $100/mes**. Incluye rastreo en tiempo real, App PWA y historial 24h. ¿Necesitas más detalles, máquina?"
    
    elif "full logistics" in prompt_lower:
        return "🚛 ¡Órale! **Full Logistics** cuesta $300/mes ($100 el primer mes). Incluye: corte de motor remoto, geocerca anti-robo, botón pánico y sensor de velocidad. Ideal para flotas en el Tren Maya, tío."
    
    elif "chip" in prompt_lower or "taxi" in prompt_lower:
        return "🚕 **CHIP TAXI** tiene tarifas desde **$45 base** (CHIP Lite). Pagos en efectivo, tarjeta o SATEC Wallet. ¿Quieres solicitar un viaje, tío?"
    
    elif "cctv" in prompt_lower or "cámara" in prompt_lower or "videovigilancia" in prompt_lower:
        return "🎥 **SATEC CCTV** ofrece videovigilancia con IA. Plan Residencial desde **$350/mes** (2-4 cámaras). Efectividad del 98% en detección de movimiento. ¿Te ayudo con una cotización, máquina?"
    
    elif "acceso" in prompt_lower or "biometría" in prompt_lower or "qr" in prompt_lower:
        return "🔐 **SATEC Access Control** ofrece biometría avanzada (huella, facial, iris) y QR dinámico. Precisión del 98.7% con latencia <0.5s. ¿Te interesa una demo, tío?"
    
    elif "precio" in prompt_lower or "costo" in prompt_lower or "plan" in prompt_lower:
        return "💰 ¡Qué padre que preguntas, máquina! Nuestros planes:\n• Básico Taxi: $100/mes\n• Full Logistics: $300/mes ($100 primer mes)\n• Fleet Pro: $250/unidad\n• CCTV Residencial: $350/mes\n• CCTV Empresarial: $890/mes\n¿Cuál te interesa, tío?"
    
    else:
        return f"📡 ¡Qué padre que preguntas, tío! Para más información sobre **SATEC NETWORK** (GPS Tracker, CHIP TAXI, CCTV o Access Control), llamanos al **+52 938 120 6643**.\n\n¿Necesitas algo específico, máquina?"

# ============================================================
# RUTAS DE LA API
# ============================================================

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('web', path)

@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('message', '').strip()
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje, tío'}), 400
        
        print(f"📨 Consulta: {user_message[:100]}")
        
        respuesta = generar_respuesta(user_message)
        
        return jsonify({'response': respuesta})
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/')
def home():
    return "¡CORELLA SATEC está viva! 🎉. El servidor funciona correctamente."

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC',
        'version': '2.0',
        'soporte': '+52 938 120 6643'
    })

# ============================================================
# INICIO
# ============================================================

# Al final del archivo, asegúrate de tener este bloque
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get("PORT", 10000)), debug=False)
