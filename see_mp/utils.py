import os
import cv2
from fastcore.basics import store_attr
from collections import Counter, namedtuple
from super_gradients.common.object_names import Models


class Config:
    "Configuration for the application."
    MODEL_NAME = Models.YOLO_NAS_M
    THRESHOLD = 0.6
    NUM_VALID_FRAMES = 15
    TARGETS = ["person", "cat"]
    HOST = os.environ.get('HOST', 'localhost')
    PORT = int(os.environ.get('PORT', 8989))
    DETECTION_URL = f'http://{HOST}:{PORT}/detections'

    # Camera stream vars, depends on the camera
    CAP_PROPS = {
        'CAP_PROP_FPS': 15,
    }


# small helper to group detection results
DetectionResult = namedtuple('DetectionResult', ['labels', 'label_names', 'confidence', 'boxes'])

def parse_det_results(results):
    """Extracts the relevant detection results from the model's prediction."""
    return DetectionResult(
        results.prediction.labels, 
        results.class_names, 
        results.prediction.confidence, 
        results.prediction.bboxes_xyxy,
    )


class DetectionManager:
    def __init__(self, targets, num_valid_frames, threshold):
        store_attr()
        self.previous_counts = {tar: 0 for tar in targets}
        self.continuous_detections = {tar: 0 for tar in targets}

    def update_detections(self, labels, label_names, confidence):
        if not len(labels):
            self.reset_continuous_counts()
            return

        counts = self.count_targets(labels, label_names, confidence)
        self.update_continuous_counts(counts)

        return counts

    def reset_continuous_counts(self):
        self.continuous_detections = {tar: 0 for tar in self.targets}

    def update_continuous_counts(self, current_counts):
        for tar in self.targets:
            self.continuous_detections[tar] = (
                self.continuous_detections[tar] + 1
                if current_counts[tar] == self.previous_counts[tar]
                else 1
            )

    def have_new_detections(self, counts):
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

    def get_latest_counts(self):
        return self.previous_counts


def draw_bounding_boxes(img, results: DetectionResult):
    """
    Draw bounding boxes and labels on the image.
    
    Args:
        img (numpy.ndarray): The input image.
        labels (numpy.ndarray): The predicted labels.
        label_names (list): The list of label names.
        confidence (numpy.ndarray): The confidence scores for each prediction.
        boxes (numpy.ndarray): The bounding box coordinates.
        
    Returns:
        numpy.ndarray: The image with bounding boxes and labels drawn.
    """
    for label, conf, box in zip(results.labels, results.confidence, results.boxes):
        label_name = results.label_names[label]
        label_text = f"{label_name} ({conf:.2f})"
        x1, y1, x2, y2 = map(int, box)
        
        img = cv2.rectangle(img, (x1, y1), (x2, y2), (255, 0, 0), 2)
        img = cv2.putText(img, label_text, (x1 - 10, y1 - 10),
                          cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

    return img
