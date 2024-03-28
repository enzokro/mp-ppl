import os
import requests
from collections import Counter
from fastcore.basics import store_attr
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer


# connection vars
HOST = os.environ.get('HOST', 'localhost')
PORT = int(os.environ.get('PORT', 8989))
DETECTION_URL = f'http://{HOST}:{PORT}/detect'

# model name and detection parameters
MODEL_NAME = Models.YOLO_NAS_S
THRESHOLD = 0.6 # TODO: class-based thresholds
NUM_VALID_FRAMES = 15

# the classes we care about
TARGETS = ["person", "cat"]


class DetectionManager:
    def __init__(self, targets, num_valid_frames, detection_url, threshold):
        store_attr()
        self.previous_counts = {tar: 0 for tar in targets}
        self.continuous_detections = {tar: 0 for tar in targets}

    def update_and_send_detections(self, labels, label_names, confidence):
        if labels.size < 1:
            self.reset_continuous_counts()
            return  # Early exit if no detections

        counts = self.count_targets(labels, label_names, confidence)
        self.update_continuous_counts(counts)

        if self.should_send_detections(counts):
            self.reset_continuous_counts()
            self.previous_counts = counts
            print(f"Sending detection data: {counts}")
            requests.post(self.detection_url, json=counts)

    def reset_continuous_counts(self):
        for tar in self.targets:
            self.continuous_detections[tar] = 0

    def update_continuous_counts(self, current_counts):
        for tar in self.targets:
            if current_counts[tar] == self.previous_counts[tar]:
                self.continuous_detections[tar] += 1
            else:
                self.continuous_detections[tar] = 1

    def should_send_detections(self, counts):
        return any(self.continuous_detections[tar] >= self.num_valid_frames for tar in self.targets) and \
               self.previous_counts != counts
    
    def count_targets(self, labels, label_names, confidence):
        """Counts the number of each target in the labels.

        Only counts if the `confidence` of a detection is above `thr`.
        """
        # Filter labels by confidence threshold first to minimize iterations
        filtered_labels = [label_names[label] for i, label in enumerate(labels) if confidence[i] >= self.threshold]
        # Utilize Counter to count occurrences of each target directly
        label_counts = Counter(filtered_labels)
        # Construct the final counts dict, ensuring all targets are included with a default of 0
        counts = {tar: label_counts.get(tar, 0) for tar in self.targets}
        return counts
    
    def set_threshold(self, thr):
        self.threshold = thr


def main():

    # Load the detection model
    model = models.get(MODEL_NAME, pretrained_weights="coco")

    # detection manager
    detection_manager = DetectionManager(TARGETS, NUM_VALID_FRAMES, DETECTION_URL, THRESHOLD)

    # Stream over the default camera
    try:
        with VideoStreamer(0) as stream:
            while True:
                img = stream.get_current_frame()
                if img is None:
                    continue

                # Detect objects in the image
                results = model.predict(img, fuse_model=False)

                # Parse out the detection results
                boxes = results.prediction.bboxes_xyxy
                label_names = results.class_names
                labels = results.prediction.labels
                confidence = results.prediction.confidence

                # run the detection manager
                detection_manager.update_and_send_detections(labels, label_names, confidence)

    except KeyboardInterrupt:
        stream.stop()
        raise stream.Break("Stopping the stream thread...")
    except Exception as e:
        raise e
    

if __name__ == "__main__":
    main()