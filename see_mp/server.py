from flask import Flask, render_template
from flask_socketio import SocketIO
import socket
import json
import os
from threading import Thread, Event

app = Flask(__name__)
socketio = SocketIO(app) 

host = os.environ.get('HOST', 'localhost')
# Port for the detection listener
detection_port = int(os.environ.get('DETECTION_PORT', 6767))
# Port for the app
flask_port = int(os.environ.get('FLASK_PORT', 8989))

# Use an Event to signal the thread to stop
stop_thread = Event()


@app.route('/')
def index():
    return render_template('index.html')

@app.route('/detect', methods=['POST'])
def handle_client_connection(conn, addr):
    print(f"Connected by {addr}")
    try:
        while not stop_thread.is_set():
            data = conn.recv(4096).decode()
            if not data:
                break
            print(f"Received data: {data}")
            detection_result = json.loads(data)
            socketio.emit('detection_result', detection_result)
    finally:
        conn.close()
        print("Connection closed by", addr)


def receive_detections():
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(1)  # Set a timeout for the accept call
    threads = []
    try:
        sock.bind((host, detection_port))
        sock.listen(1)
        print(f"Detection server listening on {host}:{detection_port}...")
        
        while not stop_thread.is_set():
            sock.settimeout(1)
            try:
                conn, addr = sock.accept()
            except socket.timeout:
                continue
            client_thread = Thread(target=handle_client_connection, args=(conn, addr))
            client_thread.start()
            threads.append(client_thread)
    finally:
        for thread in threads:
            thread.join()
        sock.close()
        print("Socket closed.")


if __name__ == '__main__':
    # Run receive_detections in its own background thread
    det_thread = Thread(target=receive_detections)
    det_thread.start()
    try:
        socketio.run(app, host=host, port=flask_port)
    except KeyboardInterrupt:
        print("Keyboard Interrupt received, shutting down.")
        stop_thread.set()  # Signal the receive_detections thread to stop
        det_thread.join()  # Wait for the detection thread to finish
        print("Shutdown complete.")
    except Exception as e:
        stop_thread.set()
        det_thread.join()
        raise e