from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import re
import os

app = Flask(__name__)
CORS(app)

# Cargar los ejemplos de entrenamiento
json_path = os.path.join(os.path.dirname(__file__), 'entrenamiento.json')
print(f"📂 Buscando archivo en: {json_path}")

try:
    with open(json_path, 'r', encoding='utf-8') as f:
        entrenamiento = json.load(f)
    print(f"✅ Cargados {len(entrenamiento)} ejemplos de entrenamiento")
except Exception as e:
    print(f"❌ Error al cargar: {e}")
    entrenamiento = []

# ========== RESPUESTAS PREDEFINIDAS COMPLETAS ==========
respuestas_predefinidas = {
    # Saludos
    "saludo": "🏨 ¡Hola! Soy Earby, tu asistente del Hotel Rosvel. ¿En qué puedo ayudarte? Pregúntame por precios, tipos de habitación (sencilla/doble/triple/familiar) o disponibilidad.",
    
    # Precios por número
    "1": "🏠 Habitación Sencilla: $680 MXN por noche para 1 persona. Incluye A/C, Wi-Fi, baño privado y TV. ¿Necesitas reservar?",
    "2": "❤️ Habitación Doble: $850 MXN por noche para 2 personas. Cama matrimonial, A/C, Wi-Fi y estacionamiento. ¿Te ayudo a reservar?",
    "3": "👨‍👩‍👧 Habitación Triple: $980 MXN por noche para 3 personas. 1 cama matrimonial + 1 individual, A/C, Wi-Fi.",
    "4": "👨‍👩‍👧‍👦 Habitación Familiar: $1,200 MXN por noche para 4 personas. 2 camas matrimoniales, 28m², A/C, Wi-Fi.",
    
    # Tipos de habitación
    "sencilla": "🏠 Habitación Sencilla: $680 MXN por noche para 1 persona. Incluye A/C, Wi-Fi, baño privado y TV.",
    "doble": "❤️ Habitación Doble: $850 MXN por noche para 2 personas. Cama matrimonial, A/C, Wi-Fi y estacionamiento.",
    "triple": "👨‍👩‍👧 Habitación Triple: $980 MXN por noche para 3 personas. 1 cama matrimonial + 1 individual, A/C, Wi-Fi.",
    "familiar": "👨‍👩‍👧‍👦 Habitación Familiar: $1,200 MXN por noche para 4 personas. 2 camas matrimoniales, 28m², A/C, Wi-Fi.",
    
    # Servicios básicos
    "precio": "💰 Precios por noche: Sencilla $680 | Doble $850 | Triple $980 | Familiar $1,200 MXN. ¡25% OFF con código NUEVO2631!",
    "cancelar": "✅ Cancelación GRATIS con 24 horas de anticipación. Sin penalización.",
    "ubicación": "📍 A 600 metros de la estación del Tren Maya en Palenque, Chiapas.",
    "estacionamiento": "🅿️ Estacionamiento gratuito en vía pública (privado bajo solicitud).",
    "wifi": "📡 Wi-Fi de alta velocidad gratis en TODAS las habitaciones.",
    "descuento": "🎁 Código NUEVO2631 para 25% DE DESCUENTO en reserva directa.",
    "whatsapp": "📞 WhatsApp: +52 938 183 4220. ¡Respondemos en minutos!",
    "horario": "⏰ Check-in: 15:00 hrs | Check-out: 12:00 hrs. Guardamos maletas.",
    "mascotas": "🐕 Consulta disponibilidad para mascotas. Llámanos al +52 938 183 4220.",
    
    # Clima / Aire acondicionado
    "clima": "❄️ ¡Claro que sí! Clima y A/C son lo mismo. Todas las habitaciones tienen aire acondicionado individual. ¡No inventes, está bien fresco!",
    
    # Amenidades de baño
    "amenidades": "🧼 ¡Sí! Incluimos jabón, shampoo, rastrillo, navaja de afeitar, papel higiénico y WC. ¡Todo para que te sientas como en casa! ¡Qué tal!!",
    
    # Colchas
    "colcha": "🛏️ ¡Sí! Todas las habitaciones incluyen colcha y ropa de cama completa, súper cómoda y limpia.",
    
    # Cama baja
    "cama_baja": "🛌 ¡Sí! Podemos darte una cama baja si la pides en recepción. ¡Dale, sin problema!",
    
    # Medicamentos
    "medicamentos": "💊 Uy, lo siento. No tenemos medicamentos. ¡Puff! Hay una farmacia bien cerca. ¿Te ayudo con la dirección?",
    
    # Grupos grandes
    "grupo": "📞 ¡Claro! Con todo gusto. Déjanos tus datos y nos ponemos en contacto. ¡Qué tal!!",
    
    # Accesibilidad
    "accesibilidad": "♿ ¡Claro que sí! Tenemos habitaciones en planta baja, sin barreras. ¡Con todo gusto te ayudamos!",
    
    # Alimentación
    "comida": "☕ Uy, todavía no tenemos restaurante. ¡Pero! Te ofrecemos un cafecito por la mañana y te sugerimos restaurantes buenísimos bien cerca.",
    
    # Alberca
    "alberca": "🌊 Puff, ya no tenemos alberca. ¡Pero! Palenque tiene 18 cascadas bien chidas para nadar. ¿Te gustan las cascadas?",
    
    # WC, regadera, espejo, tocador
    "baño": "🚽 Todas nuestras habitaciones tienen baño privado completo: WC, regadera con agua caliente, espejo y tocador amplio.",
    
    # Fumar
    "fumar": "🚭 No se permite fumar dentro de las habitaciones. Puedes fumar en la terraza o áreas exteriores.",
    
    # Microondas / Cocinar
    "microondas": "🔥 No tenemos estufa, pero ¡sí! Tenemos microondas disponible en recepción para calentar tus alimentos.",
    
    # Toallas
    "toallas": "🧺 Toallas de baño y manos incluidas. Puedes pedir extras en recepción sin costo.",
    
    # Agua caliente
    "agua": "💧 Agua caliente disponible 24/7 en todas las habitaciones.",
    
    # TV
    "tv": "📺 TV con 50+ canales de cable, incluido en todas las habitaciones.",
    
    # Tours
    "tours": "🗺️ Tenemos convenio con agencias locales. Tours a Cascadas Roberto Barrios, Welib Ha y Zona Arqueológica.",
    
    # Factura
    "factura": "📄 Sí, facturamos con RFC y uso de CFDI. Solicítala en recepción antes del check-out."
}

def buscar_respuesta(mensaje):
    mensaje_original = mensaje
    mensaje = mensaje.lower().strip()
    
    # 1. Saludos
    if mensaje in ['hola', 'buenas', 'hola earby', 'hey', 'saludos', 'buen día', 'buenas tardes', 'buenas noches']:
        return respuestas_predefinidas["saludo"]
    
    # 2. Números sueltos
    if mensaje in ["1", "2", "3", "4"]:
        return respuestas_predefinidas[mensaje]
    
    # 3. Palabras clave directas
    clave_respuesta = {
        "clima": ["clima", "aire", "ac", "aire acondicionado", "fresco", "calor"],
        "amenidades": ["jabón", "shampoo", "rastrillo", "navaja", "papel", "wc", "sanitario"],
        "colcha": ["colcha", "cobija", "sábanas", "ropa de cama"],
        "cama_baja": ["cama baja", "bajo de manda", "cama a nivel"],
        "medicamentos": ["medicamento", "aspirina", "botiquín", "pastilla"],
        "grupo": ["5 personas", "6 personas", "7 personas", "8 personas", "9 personas", "10 personas", "11 personas", "12 personas", "grupo"],
        "accesibilidad": ["silla ruedas", "discapacidad", "muletas", "capacidades diferentes", "planta baja"],
        "comida": ["desayuno", "comida", "restaurante", "café", "cafecito"],
        "alberca": ["alberca", "piscina", "jacuzzi", "pileta"],
        "baño": ["wc", "regadera", "espejo", "tocador", "sanitario", "ducha"],
        "fumar": ["fumar", "cigarro", "tabaco", "vape", "cigarrillo"],
        "microondas": ["microondas", "cocinar", "calentar", "estufa"],
        "toallas": ["toalla", "toallas"],
        "agua": ["agua caliente", "agua fría", "boiler"],
        "tv": ["tv", "televisión", "canales", "cable"],
        "tours": ["tour", "tours", "cascadas", "ruinas", "excursión"],
        "factura": ["factura", "facturar", "cfdi", "rfc"]
    }
    
    for clave, palabras in clave_respuesta.items():
        for palabra in palabras:
            if palabra in mensaje:
                return respuestas_predefinidas.get(clave, respuestas_predefinidas["saludo"])
    
    # 4. Detectar números dentro de frases
    if re.search(r'\b1\b|\buno\b|una persona|individual|solo', mensaje):
        return respuestas_predefinidas["1"]
    if re.search(r'\b2\b|\bdos\b|pareja|matrimonial|esposa|esposo', mensaje):
        return respuestas_predefinidas["2"]
    if re.search(r'\b3\b|\btres\b|triple|3 personas', mensaje):
        return respuestas_predefinidas["3"]
    if re.search(r'\b4\b|\bcuatro\b|familiar|familia|grupo', mensaje):
        return respuestas_predefinidas["4"]
    
    # 5. Buscar en el entrenamiento JSON
    if entrenamiento:
        mejor_match = None
        max_coincidencias = 0
        
        for ejemplo in entrenamiento:
            input_text = ejemplo.get('input', '').lower()
            palabras_mensaje = re.findall(r'[a-záéíóúñ]+', mensaje)
            coincidencias = 0
            
            for palabra in palabras_mensaje:
                if len(palabra) >= 3 and palabra in input_text:
                    coincidencias += 1
            
            if coincidencias > max_coincidencias and coincidencias >= 1:
                max_coincidencias = coincidencias
                mejor_match = ejemplo
        
        if mejor_match:
            respuestas = mejor_match.get('output', {}).get('respuestas_sugeridas', [])
            for r in respuestas:
                if r.get('tono') == 'amigable':
                    return r.get('texto')
            if respuestas:
                return respuestas[0].get('texto')
    
    # 6. Si nada funciona
    return "🤔 No entendí tu consulta. Puedo ayudarte con:\n• Precios: escribe 1,2,3,4\n• Servicios: wifi, estacionamiento, cancelación\n• Ubicación, descuentos, horarios\n• Amenidades: jabón, shampoo, toallas\n• Contacto: WhatsApp +52 938 183 4220\n\n¿Qué necesitas saber?"

@app.route('/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        mensaje = data.get('mensaje', '')
        respuesta = buscar_respuesta(mensaje)
        print(f"📝 Pregunta: {mensaje[:50]}...")
        return jsonify({'respuesta': respuesta})
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'respuesta': f'Error: {str(e)}'})

@app.route('/')
def home():
    return jsonify({'status': 'Earby API funcionando', 'ejemplos': len(entrenamiento)})

if __name__ == '__main__':
    print("=" * 50)
    print("🚀 Earby API - Hotel Rosvel")
    print(f"📊 Entrenamiento: {len(entrenamiento)} ejemplos")
    print("=" * 50)
    app.run(host='0.0.0.0', port=10000)