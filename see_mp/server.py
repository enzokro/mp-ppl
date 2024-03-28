from flask import Flask, render_template
from flask_socketio import SocketIO
import socket
import json

app = Flask(__name__)
socketio = SocketIO(app)

@app.route('/')
def index():
    return render_template('index.html')

def receive_detections():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    host = socket.gethostbyname("localhost")
    sock.bind((host, 6767))
    sock.listen(1)

    print("Server is waiting for a connection...")
    conn, addr = sock.accept()
    print(f"Connected by {addr}")

    while True:
        data = conn.recv(1024).decode()
        if not data:
            break
        print(f"Received data: {data}")
        detection_result = json.loads(data)
        socketio.emit('detection_result', detection_result)

    conn.close()
    print("Connection closed")

if __name__ == '__main__':
    socketio.start_background_task(receive_detections)
    socketio.run(app, port=8765)