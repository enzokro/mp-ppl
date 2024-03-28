import os
from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO

app = Flask(__name__)
socketio = SocketIO(app)

# Configuration
HOST = os.environ.get('HOST', 'localhost')
PORT = int(os.environ.get('PORT', 8989))

@app.route('/')
def index():
    """Renders the main site."""
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def handle_detection():
    """Handles the detections from the client."""
    detection_data = request.json
    print(f"Received detection data: {detection_data}")
    
    # Emit the detection result to connected WebSocket clients
    socketio.emit('detection_result', detection_data)
    
    return jsonify({"status": "received"})

def run_server():
    """Runs the application."""
    socketio.run(app, host=HOST, port=PORT)

if __name__ == '__main__':
    try:
        run_server()
    except KeyboardInterrupt:
        print("Keyboard Interrupt received, shutting down...")
    except Exception as e:
        print(f"Error: {e}")
        raise