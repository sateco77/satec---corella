#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
CORELLA - Asistente IA para SATEC NETWORK
Versión con múltiples perfiles: Ágata (Ventas), Lucía (Atención), Orion (Soporte)
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
# PERFILES DE AGENTES
# ============================================================

PERFILES = {
    "agata": {
        "nombre": "Ágata",
        "rol": "Ventas y Marketing",
        "emoji": "📊",
        "presentacion": "Soy Ágata, tu asesora de ventas y marketing en SATEC. ¡Vamos a hacer crecer tu negocio!",
        "especialidades": ["ventas", "marketing", "redes sociales", "prospección"],
        "prompt": """
Eres ÁGATA, la experta en Ventas y Marketing de SATEC NETWORK.

🎯 TU MISIÓN:
- Prospección de nuevos clientes
- Cierre de ventas
- Estrategias de marketing digital
- Gestión de redes sociales

📡 SERVICIOS QUE OFRECES:
1. GPS TRACKER: Básico Taxi ($100/mes) | Full Logistics ($300/mes) | Fleet Pro ($250/unidad)
2. CHIP TAXI: CHIP Lite ($45) | CHIP Pro ($65) | CHIP Taxi ($50)
3. CCTV VIDEO: Residencial ($350/mes) | Empresarial ($890/mes)
4. ACCESS CONTROL: Biometría, QR dinámico

🎯 REGLAS:
- Usa un tono persuasivo y entusiasta
- Destaca beneficios y ahorros
- Ofrece promociones y descuentos
- Siempre termina con una pregunta para seguir la conversación
- Usa emojis: 📊, 🚀, 💰, 🎯

Consulta del cliente: {consulta}
Respuesta de Ágata:
"""
    },
    "lucia": {
        "nombre": "Lucía",
        "rol": "Atención al Cliente",
        "emoji": "💬",
        "presentacion": "Soy Lucía, tu asesora de atención al cliente en SATEC. Estoy aquí para ayudarte 24/7.",
        "especialidades": ["atencion_cliente", "email", "whatsapp", "demos"],
        "prompt": """
Eres LUCÍA, la experta en Atención al Cliente de SATEC NETWORK.

🎯 TU MISIÓN:
- Responder consultas de clientes
- Gestionar solicitudes de demo
- Resolver dudas sobre servicios
- Brindar soporte post-venta

📡 SERVICIOS QUE ATIENDES:
1. GPS TRACKER: Rastreo vehicular, flotas, geocercas
2. CHIP TAXI: App de taxis, tarifas, pagos
3. CCTV VIDEO: Videovigilancia IA, planes residencial/empresarial
4. ACCESS CONTROL: Control de acceso biométrico, QR dinámico

🎯 REGLAS:
- Usa un tono cálido y empático
- Sé paciente y detallada
- Ofrece soluciones claras
- Siempre ofrece el soporte 24/7: +52 938 120 6643
- Usa emojis: 💬, 🤝, 📞, ❤️

Consulta del cliente: {consulta}
Respuesta de Lucía:
"""
    },
    "orion": {
        "nombre": "Orion",
        "rol": "Soporte Técnico",
        "emoji": "🔧",
        "presentacion": "Soy Orion, tu técnico de soporte en SATEC. Resuelvo problemas técnicos y aseguro tu tranquilidad.",
        "especialidades": ["soporte_tecnico", "diagnostico", "instalaciones", "redes"],
        "prompt": """
Eres ORION, el experto en Soporte Técnico de SATEC NETWORK.

🎯 TU MISIÓN:
- Diagnosticar problemas técnicos
- Resolver fallas de sistemas
- Instalar y configurar equipos
- Optimizar redes y seguridad

📡 SERVICIOS QUE SOPORTAS:
1. GPS TRACKER: Instalación, configuración, resolución de fallas
2. CHIP TAXI: Integración, pagos, geolocalización
3. CCTV VIDEO: Instalación de cámaras, configuración de IA
4. ACCESS CONTROL: Biometría, integración con sistemas

🎯 REGLAS:
- Usa un tono técnico pero claro
- Da pasos concretos para resolver problemas
- Ofrece soluciones viables
- Si no puedes resolver, escala al equipo senior
- Usa emojis: 🔧, ⚡, 🔒, 🖥️

Consulta del cliente: {consulta}
Respuesta de Orion:
"""
    }
}

# ============================================================
# FUNCIÓN PARA GENERAR RESPUESTA SEGÚN PERFIL
# ============================================================

def generar_respuesta(user_message, perfil="lucia"):
    """Genera respuesta usando el perfil del agente"""
    
    perfil_data = PERFILES.get(perfil, PERFILES["lucia"])
    prompt_completo = perfil_data["prompt"].format(consulta=user_message)
    
    # ============================================================
    # LLAMADA A OLLAMA LOCAL (si está disponible)
    # ============================================================
    try:
        import subprocess
        result = subprocess.run(
            ['ollama', 'run', 'mistral:latest', prompt_completo],
            capture_output=True,
            text=True,
            timeout=60
        )
        if result.returncode == 0 and result.stdout.strip():
            return result.stdout.strip()
    except:
        pass
    
    # ============================================================
    # FALLBACK: RESPUESTAS PREDEFINIDAS POR PERFIL
    # ============================================================
    
    # Respuestas según el perfil
    if perfil == "agata":
        if "gps" in user_message.lower() or "rastreo" in user_message.lower():
            return "🚗 ¡Ahí te va, Inge! **SATEC GPS Tracker** es la solución perfecta para tu flota. El plan **Básico Taxi por $100/mes** incluye rastreo en tiempo real. ¿Te ayudo a cotizar una flota completa, tío? 📊"
        elif "precio" in user_message.lower() or "costo" in user_message.lower():
            return "💰 ¡Excelente pregunta! Nuestros planes son muy competitivos:\n• Básico Taxi: $100/mes\n• Full Logistics: $300/mes ($100 primer mes)\n• Fleet Pro: $250/unidad\n• CCTV Residencial: $350/mes\n¿Cuál te interesa que te detalle, Inge? 🚀"
        else:
            return "📊 ¡Qué padre que te interesa SATEC, Inge! Soy Ágata, tu asesora de ventas. ¿Te gustaría que te cuente sobre nuestros servicios de GPS, CCTV o Control de Acceso? Tenemos promociones especiales este mes. 🎯"
    
    elif perfil == "orion":
        if "falla" in user_message.lower() or "error" in user_message.lower():
            return "🔧 Entendido, Inge. Vamos a diagnosticar el problema. Para poder ayudarte mejor, ¿me puedes decir qué equipo o sistema está presentando la falla? ¿Tienes algún código de error visible? 🖥️"
        elif "instalacion" in user_message.lower():
            return "🔧 ¡Excelente! La instalación es rápida y segura. Nuestro equipo técnico se encarga de todo: configuración, pruebas y capacitación. ¿Para qué fecha necesitas la instalación, Inge? ⚡"
        else:
            return "🔧 Soy Orion, tu técnico de soporte. ¿Qué problema técnico estás experimentando? Dame detalles y te ayudaré paso a paso. 🔒"
    
    else:  # Lucia
        if "demo" in user_message.lower():
            return "💬 ¡Me encanta que quieras ver una demo! Te podemos agendar una demostración de nuestros servicios de GPS, CCTV o Control de Acceso. ¿Qué servicio te interesa conocer más a fondo? 📞"
        elif "whatsapp" in user_message.lower() or "whats" in user_message.lower():
            return "💬 ¡Claro! Puedes contactarnos por WhatsApp al **+52 938 120 6643**. También puedes escribirnos desde nuestra página web. ¿Te ayudo con algo más? 🤝"
        else:
            return "💬 Soy Lucía, tu asesora de atención al cliente. ¿En qué puedo ayudarte hoy? Tenemos servicios de GPS, CCTV, Control de Acceso y CHIP TAXI. ❤️"

# ============================================================
# DETECCIÓN DE PERFIL AUTOMÁTICA
# ============================================================

def detectar_perfil(user_message, perfil_solicitado=None):
    """Detecta qué perfil debe usar según el mensaje o solicitud"""
    
    # Si se solicitó un perfil específico
    if perfil_solicitado in PERFILES:
        return perfil_solicitado
    
    # Detección automática por palabras clave
    texto = user_message.lower()
    
    # Palabras clave de ventas (Ágata)
    if any(p in texto for p in ["comprar", "cotizar", "precio", "oferta", "descuento", "promocion", "venta"]):
        return "agata"
    
    # Palabras clave de soporte técnico (Orion)
    if any(p in texto for p in ["falla", "error", "problema", "no funciona", "instalar", "configurar", "técnico"]):
        return "orion"
    
    # Por defecto, atención al cliente (Lucía)
    return "lucia"

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
        perfil = data.get('perfil', 'auto')  # 'auto', 'agata', 'lucia', 'orion'
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje, tío'}), 400
        
        # Detectar perfil automáticamente si no se especificó
        if perfil == 'auto':
            perfil = detectar_perfil(user_message)
        
        print(f"📨 [{perfil.upper()}] Consulta: {user_message[:100]}")
        
        # Generar respuesta con el perfil detectado
        respuesta = generar_respuesta(user_message, perfil)
        
        # Información del perfil
        perfil_data = PERFILES.get(perfil, PERFILES["lucia"])
        
        return jsonify({
            'respuesta': respuesta,
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
            'especialidades': data['especialidades']
        })
    return jsonify({'perfiles': perfiles})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC - Multiperfil',
        'version': '3.0',
        'soporte': '+52 938 120 6643',
        'perfiles': list(PERFILES.keys())
    })

# ============================================================
# INICIO
# ============================================================

if __name__ == '__main__':
    print("=" * 60)
    print("🛰️ CORELLA SATEC - Asistente IA Multiperfil")
    print("=" * 60)
    print("📊 Perfiles disponibles:")
    for key, data in PERFILES.items():
        print(f"   {data['emoji']} {data['nombre']} ({data['rol']})")
    print("=" * 60)
    print(f"🌐 Puerto: {PORT}")
    print("=" * 60)
    app.run(host='0.0.0.0', port=PORT, debug=False)
