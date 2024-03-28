import json
import zmq
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer


# zmq vars
PROTOCOL = "tcp"
PORT = 6767

# model name and threshold value
MODEL_NAME = Models.YOLO_NAS_S
THRESHOLD = 0.6

# the classes we care about
targets = ["person", "cat"]


def count_targets(labels, label_names, confidence, thr=THRESHOLD):
    """Counts the number of each target in the labels.
    
    Only counts if the `confidence` of a detection is above `thr`.
    """
    counts = {tar: 0 for tar in targets}
    for tar in targets:
        count = sum([1 for i,l in enumerate(labels) if label_names[l] == tar
                                                    and confidence[i] >= thr])
        counts[tar] = count
    return counts


def main():
    # Initialize ZeroMQ socket for sending detections
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"{PROTOCOL}://*:{PORT}")

    # Load the detection model
    model = models.get(MODEL_NAME, pretrained_weights="coco")

    # Number of frames for an updated decision
    num_valid_frames = 15
    previous_counts = {tar: 0 for tar in targets}
    continuous_detections = {tar: 0 for tar in targets}

    # Stream over the default camera
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

            # Small check if there are no detections
            if labels.size < 1:
                text = "No detections."
                response = {"text": text}
                # Reset continuous detections count for each target
                for tar in targets:
                    continuous_detections[tar] = 0
            else:
                # Count the number of each target
                counts = count_targets(labels, label_names, confidence)

                # Update continuous detections count for each target
                for tar in targets:
                    if counts[tar] == previous_counts[tar]:
                        continuous_detections[tar] += 1
                    else:
                        continuous_detections[tar] = 1

                # Check if the number of continuous detections exceeds the minimum threshold
                if any(continuous_detections[tar] >= num_valid_frames for tar in targets):
                    # Prepare the response only if there is a change in the counts
                    if counts != previous_counts:
                        previous_counts = response = counts
                        # Reset continuous detections count for each target
                        for tar in targets:
                            continuous_detections[tar] = 0
                    else:
                        response = {}
                else:
                    response = {}

            # Send the JSON response over ZeroMQ socket if there is a response
            if response:
                print(response)
                json_response = json.dumps(response)
                socket.send_string(json_response)


if __name__ == "__main__":
    main()