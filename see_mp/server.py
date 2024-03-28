from flask import Flask, render_template, request, jsonify
from flask_socketio import SocketIO
import socket
import json
import os
from threading import Thread, Event

app = Flask(__name__)
socketio = SocketIO(app) 

host = os.environ.get('HOST', 'localhost')
port = int(os.environ.get('PORT', 8989))

# Use an Event to signal the thread to stop
stop_thread = Event()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def handle_detection():
    # Assuming detection data is sent as JSON in the POST request body
    detection_data = request.json
    print(f"Received detection data: {detection_data}")
    
    # Emit the detection result to connected WebSocket clients
    socketio.emit('detection_result', detection_data)
    
    # Respond to the HTTP request to acknowledge receipt
    return jsonify({"status": "received"})


if __name__ == '__main__':
    try:
        socketio.run(app, host=host, port=port)
    except KeyboardInterrupt:
        print("Keyboard Interrupt received, shutting down...")
        exit(0)
    except Exception as e:
        raise