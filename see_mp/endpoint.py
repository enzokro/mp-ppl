import atexit
import threading
from flask import Flask, jsonify
from super_gradients.training import models
from see_mp.video_stream import VideoStreamer
from see_mp.utils import DetectionManager, Config

app = Flask(__name__)

class SharedResources:
   """Shared resources accessible by multiple threads."""
   def __init__(self):
       self.model = models.get(Config.MODEL_NAME, pretrained_weights="coco")
       self.detection_manager = DetectionManager(Config.TARGETS, Config.NUM_VALID_FRAMES, Config.THRESHOLD)
       self.detection_lock = threading.Lock()
       self.shutdown_event = threading.Event()

shared_resources = SharedResources()

class DetectionThread(threading.Thread):
   """Thread for continuous object detection."""
   def __init__(self, shared_resources):
       super().__init__(daemon=True)
       self.shared_resources = shared_resources

   def run(self):
       """Main loop for object detection."""
       print("Detection thread starting...")
       video_streamer = VideoStreamer(0, capture_props=Config.CAP_PROPS)
       video_streamer.start()

       while not self.shared_resources.shutdown_event.is_set():
           frame = video_streamer.get_current_frame()
           if frame is None:
               continue

           results = self.shared_resources.model.predict(frame, fuse_model=False)
           self._process_detections(results)

           if self.shared_resources.shutdown_event.is_set():
               break

       video_streamer.stop()
       print("Detection thread exiting.")

   def _process_detections(self, results):
       """Process detection results and update detection manager."""
       with self.shared_resources.detection_lock:
           counts = self.shared_resources.detection_manager.update_detections(
               results.prediction.labels,
               results.class_names,
               results.prediction.confidence)
           if self.shared_resources.detection_manager.have_new_detections(counts):
               self.shared_resources.detection_manager.reset_continuous_counts()
               self.shared_resources.detection_manager.previous_counts = counts

# Start detection thread
detection_thread = DetectionThread(shared_resources)
detection_thread.start()

@app.route('/detections', methods=['GET'])
def get_detections():
   """Endpoint to get the latest detections."""
   with shared_resources.detection_lock:
       counts = shared_resources.detection_manager.get_latest_counts()
   return jsonify(counts)

def cleanup():
   """Cleanup function to gracefully shutdown the application."""
   print("Application is shutting down. Cleaning up resources.")
   shared_resources.shutdown_event.set()
   detection_thread.join()

atexit.register(cleanup)

if __name__ == "__main__":
   app.run(host=Config.HOST, port=Config.PORT)