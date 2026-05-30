import os
import json
from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS

app = Flask(__name__, static_folder='web')
CORS(app)

PORT = int(os.environ.get("PORT", 10000))

@app.route('/')
def index():
    return send_from_directory('web', 'index.html')

@app.route('/<path:path>')
def static_files(path):
    return send_from_directory('web', path)

@app.route('/api/health', methods=['GET'])
def health():
    return jsonify({
        'status': 'ok',
        'service': 'CORELLA SATEC',
        'version': '2.0',
        'soporte': '+52 938 120 6643'
    })

@app.route('/api/chat', methods=['POST', 'GET'])
def chat():
    # Manejar GET para pruebas
    if request.method == 'GET':
        return jsonify({'response': 'El endpoint /api/chat funciona. Envía un POST con {"message": "tu pregunta"}'})
    
    # Manejar POST
    try:
        # Intentar obtener JSON del body
        if request.is_json:
            data = request.get_json()
            user_message = data.get('message', '')
        else:
            # Si no es JSON, intentar leer como form
            user_message = request.form.get('message', '')
        
        if not user_message:
            user_message = request.args.get('message', '')
        
        print(f"📨 Mensaje recibido: {user_message}")
        
        # Respuesta de prueba
        respuesta = f"Hola Inge, soy CORELLA de SATEC. Recibí tu mensaje: '{user_message}'. ¿Necesitas ayuda con GPS Tracker, CHIP TAXI, CCTV o Control de Acceso? Llámanos al 938 120 6643."
        
        return jsonify({'response': respuesta})
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'response': f'Error: {str(e)}'}), 500

if __name__ == '__main__':
    print("=" * 50)
    print("🛰️ CORELLA SATEC - Servidor Activo")
    print("=" * 50)
    print(f"🌐 Puerto: {PORT}")
    print("=" * 50)
    app.run(host='0.0.0.0', port=PORT, debug=False)
