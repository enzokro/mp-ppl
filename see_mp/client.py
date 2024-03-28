import os
from collections import Counter, namedtuple
import requests
import fire
from fastcore.basics import store_attr
from fastcore.foundation import L
import cv2
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer


# The classes we care about
TARGETS = ["person", "cat"]

# Connection vars
HOST = os.environ.get('HOST', 'localhost')
PORT = int(os.environ.get('PORT', 8989))
DETECTION_URL = f'http://{HOST}:{PORT}/detect'

# Camera stream vars, depends on the camera
CAP_PROPS = {
    'CAP_PROP_FPS': 15,
}

# Model name and detection parameters
MODEL_NAME = Models.YOLO_NAS_M
THRESHOLD = 0.6  # TODO: class-based thresholds
NUM_VALID_FRAMES = 15

# small helper to group detection results
DetectionResult = namedtuple('DetectionResult', ['labels', 'label_names', 'confidence', 'boxes'])


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


def draw_bounding_boxes(img, results):
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


def parse_det_results(results):
    """Extracts the relevant detection results from the model's prediction."""
    return DetectionResult(
        results.prediction.labels, 
        results.class_names, 
        results.prediction.confidence, 
        results.prediction.bboxes_xyxy,
    )


def main(
        draw: bool = False,
):
    # Load the detection model
    model = models.get(MODEL_NAME, pretrained_weights="coco")

    # Detection manager
    detection_manager = DetectionManager(TARGETS, NUM_VALID_FRAMES, THRESHOLD)

    # Stream over the default camera
    with VideoStreamer(0, capture_props=CAP_PROPS) as stream:
        try:
            while True:
                img = stream.get_current_frame()
                if img is None:
                    continue
                
                # for optional drawing
                output_img = img.copy() if draw else None

                # Detect objects in the image
                results = model.predict(img, fuse_model=False)

                # Parse out the detection results
                results = parse_det_results(results)

                # Run the detection manager
                counts = detection_manager.update_detections(
                    results.labels, results.label_names, results.confidence
                )

                if detection_manager.have_new_detections(counts):
                    detection_manager.reset_continuous_counts()
                    detection_manager.previous_counts = counts
                    print(f"Sending detection data: {counts}")

                    try:
                        response = requests.post(DETECTION_URL, json=counts)
                        response.raise_for_status()
                    except requests.exceptions.RequestException as e:
                        print(f"Error sending detection data: {e}")

                if draw:
                    output_img = draw_bounding_boxes(output_img, results)
                    cv2.imshow("Results", output_img)
                    if cv2.waitKey(1) == ord('q'):
                        raise stream.Break

        except KeyboardInterrupt:
            print("Stopping the stream thread...")
        except Exception as e:
            print(f"Error: {e}")
            raise

if __name__ == "__main__":
    fire.Fire(main)