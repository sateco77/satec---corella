import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

# Respuestas profesionales de SATEC
respuestas = {
    "gps": "SATEC GPS Tracker ofrece tres planes: Básico Taxi por $100 mensuales (rastreo en tiempo real), Full Logistics por $300 mensuales ($100 el primer mes) que incluye corte de motor remoto, geocerca anti-robo, botón de pánico y sensor de velocidad, y Fleet Pro por $250 por unidad con integración API y reportes de combustible. ¿Necesita más información?",
    
    "chip": "CHIP TAXI es nuestra solución de movilidad. Tarifas: CHIP Lite desde $45, CHIP Taxi $50, CHIP Pro $65. Aceptamos efectivo, tarjeta, transferencia y SATEC Wallet. Todos los conductores están verificados y el viaje cuenta con rastreo en vivo.",
    
    "cctv": "SATEC CCTV ofrece videovigilancia con inteligencia artificial. Plan Residencial desde $350 mensuales (2-4 cámaras, app móvil, detección de personas) y Plan Empresarial desde $890 mensuales (8+ cámaras, IA avanzada, analíticas). Efectividad del 98% en detección de movimiento.",
    
    "access": "SATEC Access Control incluye biometría con 98.7% de precisión (huella digital, reconocimiento facial, lectura de iris), QR dinámico integrado con SATEC Wallet y protocolos Wiegand, OSDP y API REST.",
    
    "codigo": "El Código Maestro es la clave única asignada a cada cliente de SATEC, por ejemplo ST-8829-GX. Este código autoriza descargas y movimientos de activos. No debe compartirse con personal no autorizado.",
    
    "soporte": "SATEC ofrece soporte técnico 24/7 en el teléfono 938 120 6643. Nuestras oficinas están ubicadas en Palenque, Chiapas."
}

def obtener_respuesta(mensaje):
    mensaje_lower = mensaje.lower()
    
    if "gps" in mensaje_lower or "rastreo" in mensaje_lower or "flota" in mensaje_lower:
        return respuestas["gps"]
    elif "chip" in mensaje_lower or "taxi" in mensaje_lower or "viaje" in mensaje_lower:
        return respuestas["chip"]
    elif "cctv" in mensaje_lower or "camara" in mensaje_lower or "videovigilancia" in mensaje_lower:
        return respuestas["cctv"]
    elif "acceso" in mensaje_lower or "biometria" in mensaje_lower or "qr" in mensaje_lower:
        return respuestas["access"]
    elif "codigo" in mensaje_lower or "maestro" in mensaje_lower:
        return respuestas["codigo"]
    elif "soporte" in mensaje_lower or "telefono" in mensaje_lower or "contacto" in mensaje_lower:
        return respuestas["soporte"]
    else:
        return "Bienvenido a SATEC. Puedo ayudarle con información sobre GPS Tracker, CHIP TAXI, CCTV y Control de Acceso. También sobre el Código Maestro y soporte técnico. ¿Sobre qué servicio desea información?"

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
            return jsonify({'response': 'Por favor, escriba su consulta.'})
        
        print(f"📨 Consulta: {user_message}")
        respuesta = obtener_respuesta(user_message)
        print(f"✅ Respuesta enviada")
        
        return jsonify({'response': respuesta})
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'response': f'Error: {str(e)}'})

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({'status': 'ok', 'service': 'CORELLA SATEC', 'version': '2.0'})

if __name__ == '__main__':
    print("=" * 50)
    print("🛰️ CORELLA SATEC - Asistente Profesional")
    print("=" * 50)
    print(f"🌐 Puerto: {PORT}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=PORT)
