import json
import zmq
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer


PORT = 6767
MODEL_NAME = Models.YOLO_NAS_S
THR = 0.6


def initialize_zmq_socket(port):
    """Initialize ZeroMQ context and socket for sending detections."""
    context = zmq.Context()
    socket = context.socket(zmq.PUB)
    socket.bind(f"tcp://*:{port}")
    return socket


def count_targets(labels, label_names, targets, confidence, thr):
    """Count the number of each target in the labels.
    
    Makes sure detections are above `thr` in confidence.
    """
    counts = {tar: 0 for tar in targets}
    for targ in targets:
        count = sum([1 for i,l in enumerate(labels) if label_names[l] == targ
                                                    and confidence[i] >= thr])
        counts[targ] = count
    return counts

def prepare_response(counts):
    """Prepare the response dictionary with the target counts."""
    response = {
        f"num_{targ}": count 
        for targ, count in counts.items()
    }
    return response


def main():
    # Initialize ZeroMQ socket for sending detections
    results_socket = initialize_zmq_socket(PORT)

    # Load the detection model
    model = models.get(MODEL_NAME, pretrained_weights="coco")

    # Define the target classes we care about
    targets = ["person", "cat"]

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
                for targ in targets:
                    continuous_detections[targ] = 0
            else:
                # Count the number of each target
                counts = count_targets(labels, label_names, targets,
                                       confidence, THR)

                # Update continuous detections count for each target
                for targ in targets:
                    if counts[targ] == previous_counts[targ]:
                        continuous_detections[targ] += 1
                    else:
                        continuous_detections[targ] = 1

                # Check if the number of continuous detections exceeds the minimum threshold
                if any(continuous_detections[targ] >= num_valid_frames for targ in targets):
                    # Prepare the response only if there is a change in the counts
                    if counts != previous_counts:
                        response = prepare_response(counts)
                        previous_counts = counts
                        # Reset continuous detections count for each target
                        for targ in targets:
                            continuous_detections[targ] = 0
                    else:
                        response = {}
                else:
                    response = {}

            # Send the JSON response over ZeroMQ socket if there is a response
            if response:
                print(response)
                json_response = json.dumps(response)
                results_socket.send_string(json_response)


if __name__ == "__main__":
    main()