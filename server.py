@app.route('/api/chat', methods=['POST'])
def chat():
    try:
        data = request.json
        user_message = data.get('mensaje') or data.get('message', '')
        
        if not user_message:
            return jsonify({'error': 'No enviaste ningún mensaje, tío'}), 400
        
        print(f"📨 Consulta: {user_message[:100]}")
        
        respuesta = generar_respuesta(user_message)
        
        # ✅ DEVUELVE AMBOS CAMPOS
        return jsonify({
            'respuesta': respuesta,   # Para el widget
            'response': respuesta     # Compatibilidad
        })
    
    except Exception as e:
        print(f"❌ Error: {e}")
        return jsonify({'error': str(e)}), 500
