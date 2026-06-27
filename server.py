#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA Multiperfil para SATEC NETWORK
Orquestador con 3 perfiles: Ágata (Ventas), Lucía (Atención), Orion (Soporte)
"""

import os
import json
import requests
import subprocess
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

# ============================================================
# CONFIGURACIÓN
# ============================================================

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))
OLLAMA_AVAILABLE = False

# Verificar si Ollama está disponible
try:
    result = subprocess.run(['ollama', 'list'], capture_output=True, text=True, timeout=5)
    OLLAMA_AVAILABLE = result.returncode == 0
except:
    OLLAMA_AVAILABLE = False

# ============================================================
# PERFILES DE AGENTES
# ============================================================

PERFILES = {
    "agata": {
        "id": "agata",
        "nombre": "Ágata",
        "rol": "Ventas y Marketing",
        "emoji": "📊",
        "color": "#8B5CF6",
        "presentacion": "Soy Ágata, tu asesora de ventas y marketing en SATEC. ¡Vamos a hacer crecer tu negocio!",
        "especialidades": ["ventas", "marketing", "prospección", "promociones"],
        "palabras_clave": ["comprar", "cotizar", "precio", "oferta", "descuento", "promocion", "venta", "costo", "negocio", "invertir"],
        "prompt": """Eres ÁGATA, la experta en Ventas y Marketing de SATEC NETWORK.

🎯 TU MISIÓN: Prospección de clientes, cierre de ventas, estrategias de marketing.

📡 SERVICIOS QUE OFRECES:
1. GPS TRACKER: Básico Taxi ($100/mes) | Full Logistics ($300/mes, $100 primer mes) | Fleet Pro ($250/unidad)
2. CHIP TAXI: CHIP Lite ($45) | CHIP Pro ($65) | CHIP Taxi ($50)
3. CCTV VIDEO: Residencial ($350/mes) | Empresarial ($890/mes)
4. ACCESS CONTROL: Biometría, QR dinámico

🎯 REGLAS:
- Tono persuasivo y entusiasta
- Destaca beneficios y ahorros
- Ofrece promociones
- Termina con pregunta para seguir conversación
- Usa emojis: 📊, 🚀, 💰, 🎯

Consulta del cliente: {consulta}
Respuesta de Ágata:"""
    },
    "lucia": {
        "id": "lucia",
        "nombre": "Lucía",
        "rol": "Atención al Cliente",
        "emoji": "💬",
        "color": "#3B82F6",
        "presentacion": "Soy Lucía, tu asesora de atención al cliente en SATEC. Estoy aquí para ayudarte 24/7.",
        "especialidades": ["atencion_cliente", "demos", "consultas", "whatsapp"],
        "palabras_clave": ["demo", "ayuda", "duda", "consultar", "atencion", "cliente", "servicio", "contacto"],
        "prompt": """Eres LUCÍA, la experta en Atención al Cliente de SATEC NETWORK.

🎯 TU MISIÓN: Responder consultas, gestionar demos, resolver dudas, soporte post-venta.

📡 SERVICIOS QUE ATIENDES:
1. GPS TRACKER: Rastreo vehicular, flotas, geocercas
2. CHIP TAXI: App de taxis, tarifas, pagos
3. CCTV VIDEO: Videovigilancia IA
4. ACCESS CONTROL: Control de acceso biométrico

🎯 REGLAS:
- Tono cálido y empático
- Paciente y detallada
- Ofrece soluciones claras
- Siempre ofrece soporte 24/7: +52 938 120 6643
- Usa emojis: 💬, 🤝, 📞, ❤️

Consulta del cliente: {consulta}
Respuesta de Lucía:"""
    },
    "orion": {
        "id": "orion",
        "nombre": "Orion",
        "rol": "Soporte Técnico",
        "emoji": "🔧",
        "color": "#F59E0B",
        "presentacion": "Soy Orion, tu técnico de soporte en SATEC. Resuelvo problemas técnicos y aseguro tu tranquilidad.",
        "especialidades": ["soporte_tecnico", "diagnostico", "instalaciones", "redes"],
        "palabras_clave": ["falla", "error", "problema", "no funciona", "instalar", "configurar", "técnico", "soporte"],
        "prompt": """Eres ORION, el experto en Soporte Técnico de SATEC NETWORK.

🎯 TU MISIÓN: Diagnosticar problemas, resolver fallas, instalar y configurar equipos.

📡 SERVICIOS QUE SOPORTAS:
1. GPS TRACKER: Instalación, configuración, resolución de fallas
2. CHIP TAXI: Integración, pagos, geolocalización
3. CCTV VIDEO: Instalación de cámaras, configuración de IA
4. ACCESS CONTROL: Biometría, integración con sistemas

🎯 REGLAS:
- Tono técnico pero claro
- Da pasos concretos para resolver
- Ofrece soluciones viables
- Escala al equipo senior si es necesario
- Usa emojis: 🔧, ⚡, 🔒, 🖥️

Consulta del cliente: {consulta}
Respuesta de Orion:"""
    }
}

# Respuestas de fallback por perfil
FALLBACK_RESPUESTAS = {
    "agata": "📊 ¡Qué padre que te interesa SATEC, Inge! Soy Ágata, tu asesora de ventas. ¿Te gustaría que te cuente sobre nuestros servicios de GPS, CCTV o Control de Acceso? Tenemos promociones especiales este mes. 🎯",
    "lucia": "💬 Soy Lucía, tu asesora de atención al cliente. ¿En qué puedo ayudarte hoy? Tenemos servicios de GPS, CCTV, Control de Acceso y CHIP TAXI. ❤️",
    "orion": "🔧 Soy Orion, tu técnico de soporte. ¿Qué problema técnico estás experimentando? Dame detalles y te ayudaré paso a paso. 🔒"
}

# ============================================================
# FUNCIONES
# ============================================================

def detectar_perfil(user_message):
    """Detecta qué perfil debe usar según el mensaje"""
    texto = user_message.lower()
    
    # Si se menciona un perfil específico en el mensaje
    if "agata" in texto or "ventas" in texto or "marketing" in texto:
        return "agata"
    if "orion" in texto or "soporte" in texto or "técnico" in texto or "falla" in texto:
        return "orion"
    if "lucia" in texto or "atencion" in texto or "cliente" in texto or "ayuda" in texto:
        return "lucia"
    
    # Detección automática por palabras clave
    for perfil_id, perfil_data in PERFILES.items():
        for palabra in perfil_data["palabras_clave"]:
            if palabra in texto:
                return perfil_id
    
    # Por defecto, Lucía (Atención al Cliente)
    return "lucia"

def generar_respuesta_con_ollama(user_message, perfil):
    """Genera respuesta usando Ollama si está disponible"""
    if not OLLAMA_AVAILABLE:
        return None
    
    try:
        perfil_data = PERFILES.get(perfil, PERFILES["lucia"])
        prompt_completo = perfil_data["prompt"].format(consulta=user_message)
        
        result = subprocess.run(
            ['ollama', 'run', 'llama3.2:latest', prompt_completo],
            capture_output=True,
            text=True,
            timeout=60
        )
        
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
        return None
    except Exception as e:
        print(f"⚠️ Error en Ollama: {e}")
        return None

def generar_respuesta_fallback(user_message, perfil):
    """Genera respuesta de fallback según el perfil"""
    return FALLBACK_RESPUESTAS.get(perfil, FALLBACK_RESPUESTAS["lucia"])

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
        user_message = data.get('mensaje') or data.get('message', '')
        perfil_especifico = data.get('perfil', 'auto')
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje'}), 400
        
        # Detectar perfil
        if perfil_especifico == 'auto':
            perfil = detectar_perfil(user_message)
        else:
            perfil = perfil_especifico if perfil_especifico in PERFILES else 'lucia'
        
        print(f"📨 [{perfil.upper()}] Consulta: {user_message[:100]}")
        
        # Generar respuesta
        respuesta = generar_respuesta_con_ollama(user_message, perfil)
        if not respuesta:
            respuesta = generar_respuesta_fallback(user_message, perfil)
        
        perfil_data = PERFILES.get(perfil, PERFILES["lucia"])
        
        return jsonify({
            'response': respuesta,
            'perfil': perfil,
            'agente': perfil_data['nombre'],
            'rol': perfil_data['rol'],
            'emoji': perfil_data['emoji']
        })
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/perfiles', methods=['GET'])
def get_perfiles():
    """Retorna la lista de perfiles disponibles"""
    perfiles = []
    for key, data in PERFILES.items():
        perfiles.append({
            'id': key,
            'nombre': data['nombre'],
            'rol': data['rol'],
            'emoji': data['emoji'],
            'color': data['color'],
            'especialidades': data['especialidades']
        })
    return jsonify({'perfiles': perfiles})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC',
        'version': '3.0',
        'ollama': OLLAMA_AVAILABLE,
        'perfiles': list(PERFILES.keys()),
        'soporte': '+52 938 120 6643'
    })

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA Multiperfil")
    print("=" * 60)
    print(f"🧠 Ollama disponible: {'✅ Sí' if OLLAMA_AVAILABLE else '❌ No'}")
    print("\n📊 Perfiles disponibles:")
    for key, data in PERFILES.items():
        print(f"   {data['emoji']} {data['nombre']} ({data['rol']})")
    print("=" * 60)
    print(f"🌐 Puerto: {PORT}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
