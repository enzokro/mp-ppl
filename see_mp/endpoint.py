import atexit
import threading
from flask import Flask, jsonify
from super_gradients.training import models
from see_mp.video_stream import VideoStreamer
from see_mp.utils import DetectionManager, Config

app = Flask(__name__)

# Setup shared resources
model = models.get(Config.MODEL_NAME, pretrained_weights="coco")
detection_manager = DetectionManager(Config.TARGETS, Config.NUM_VALID_FRAMES, Config.THRESHOLD)
detection_lock = threading.Lock()
shutdown_event = threading.Event()

class DetectionThread(threading.Thread):
    def __init__(self, shutdown_event):
        super().__init__(daemon=True)
        self.shutdown_event = shutdown_event

    def run(self):
        print("Detection thread starting...")
        video_streamer = VideoStreamer(0, capture_props=Config.CAP_PROPS)
        video_streamer.start()

        while not self.shutdown_event.is_set():
            frame = video_streamer.get_current_frame()
            if frame is None:
                continue

            results = model.predict(frame, fuse_model=False)
            with detection_lock:
                counts = detection_manager.update_detections(
                    results.prediction.labels,
                    results.class_names,
                    results.prediction.confidence)
                if detection_manager.have_new_detections(counts):
                    detection_manager.reset_continuous_counts()
                    detection_manager.previous_counts = counts
            
            if self.shutdown_event.is_set():
                break

        video_streamer.stop()
        print("Detection thread exiting.")

# Start detection thread
detection_thread = DetectionThread(shutdown_event)
detection_thread.start()

@app.route('/detections', methods=['GET'])
def get_detections():
    with detection_lock:
        counts = detection_manager.get_latest_counts()
    return jsonify(counts)

def cleanup():
    print("Application is shutting down. Cleaning up resources.")
    shutdown_event.set()
    if detection_thread.is_alive():
        detection_thread.join()

atexit.register(cleanup)

if __name__ == "__main__":
    app.run(host=Config.HOST, port=Config.PORT)
