import os
from flask import Flask, jsonify
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer
from see_mp.utils import DetectionManager, Config
import threading

# create the Flask app
app = Flask(__name__)

# load the detection model
model = models.get(Config.MODEL_NAME, pretrained_weights="coco")

# manages and filters detections
detection_manager = DetectionManager(Config.TARGETS, Config.NUM_VALID_FRAMES, Config.THRESHOLD)

# streams video frames from the default camera
video_streamer = VideoStreamer(0, capture_props=Config.CAP_PROPS)

# Lock for thread-safe access to detection_manager
detection_lock = threading.Lock()
# Event to signal the detection thread to stop
stop_event = threading.Event()


def process_detections():
    "Continuously process detections and update the detection manager."
    while not stop_event.is_set():
        frame = video_streamer.get_current_frame()
        if frame is None:
            continue

        results = model.predict(frame, fuse_model=False)
        labels = results.prediction.labels
        label_names = results.class_names
        confidence = results.prediction.confidence
        boxes = results.prediction.bboxes_xyxy

        with detection_lock:
            counts = detection_manager.update_detections(labels, label_names, confidence)
            if detection_manager.have_new_detections(counts):
                detection_manager.reset_continuous_counts()
                detection_manager.previous_counts = counts

        # Check for the stop signal periodically
        if stop_event.is_set():
            break


@app.route('/detections', methods=['GET'])
def get_detections():
    "Gets the latest detections."
    with detection_lock:
        counts = detection_manager.get_latest_counts()
    return jsonify(counts)


def start_detection_thread():
    "Start the detection thread."
    detection_thread = threading.Thread(target=process_detections)
    detection_thread.start()
    return detection_thread

def stop_detection_thread():
    "Stop the detection thread."
    stop_event.set()


def main():
    "Main function to start the video streaming, detection processing, and run the Flask app."
    video_streamer.start()

    detection_thread = start_detection_thread()

    try:
        app.run(host=Config.HOST, port=Config.PORT)
    except KeyboardInterrupt:
        print("Keyboard interrupt received. Shutting down gracefully...")
    finally:
        stop_detection_thread()
        video_streamer.stop()
        detection_thread.join()

if __name__ == "__main__":
    main()