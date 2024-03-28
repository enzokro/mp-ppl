import os
from collections import Counter
import requests
from fastcore.basics import store_attr
from fastcore.foundation import L
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer

# Connection vars
HOST = os.environ.get('HOST', 'localhost')
PORT = int(os.environ.get('PORT', 8989))
DETECTION_URL = f'http://{HOST}:{PORT}/detect'

# Model name and detection parameters
MODEL_NAME = Models.YOLO_NAS_M
THRESHOLD = 0.6  # TODO: class-based thresholds
NUM_VALID_FRAMES = 15

# The classes we care about
TARGETS = ["person", "cat"]

class DetectionManager:
    def __init__(self, targets, num_valid_frames, detection_url, threshold):
        store_attr()
        self.previous_counts = {tar: 0 for tar in targets}
        self.continuous_detections = {tar: 0 for tar in targets}

    def update_and_send_detections(self, labels, label_names, confidence):
        if not len(labels):
            self.reset_continuous_counts()
            return

        counts = self.count_targets(labels, label_names, confidence)
        self.update_continuous_counts(counts)

        if self.should_send_detections(counts):
            self.reset_continuous_counts()
            self.previous_counts = counts
            print(f"Sending detection data: {counts}")
            self._send_detections(counts)

    def _send_detections(self, counts):
        try:
            response = requests.post(self.detection_url, json=counts)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            print(f"Error sending detection data: {e}")

    def reset_continuous_counts(self):
        self.continuous_detections = {tar: 0 for tar in self.targets}

    def update_continuous_counts(self, current_counts):
        for tar in self.targets:
            self.continuous_detections[tar] = (
                self.continuous_detections[tar] + 1
                if current_counts[tar] == self.previous_counts[tar]
                else 1
            )

    def should_send_detections(self, counts):
        return (
            any(self.continuous_detections[tar] >= self.num_valid_frames for tar in self.targets)
            and self.previous_counts != counts
        )

    def count_targets(self, labels, label_names, confidence):
        """
        Counts the number of each target in the labels.
        Only counts if the `confidence` of a detection is above the threshold.
        """
        filtered_labels = [label_names[label] for label, conf in zip(labels, confidence) if conf >= self.threshold]
        label_counts = Counter(filtered_labels)
        return {tar: label_counts.get(tar, 0) for tar in self.targets}

    def set_threshold(self, threshold):
        self.threshold = threshold

def main():
    # Load the detection model
    model = models.get(MODEL_NAME, pretrained_weights="coco")

    # Detection manager
    detection_manager = DetectionManager(TARGETS, NUM_VALID_FRAMES, DETECTION_URL, THRESHOLD)

    # Stream over the default camera
    with VideoStreamer(0) as stream:
        try:
            while True:
                img = stream.get_current_frame()
                if img is None:
                    continue

                # Detect objects in the image
                results = model.predict(img, fuse_model=False)

                # Parse out the detection results
                labels = results.prediction.labels
                label_names = results.class_names
                confidence = results.prediction.confidence
                # TODO: draw things with the boxes
                boxes = results.prediction.bboxes_xyxy

                # Run the detection manager
                detection_manager.update_and_send_detections(labels, label_names, confidence)

        except KeyboardInterrupt:
            print("Stopping the stream thread...")
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    main()