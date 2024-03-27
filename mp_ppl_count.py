import json
import zmq
from super_gradients.training import models
from super_gradients.common.object_names import Models
from chaski.dets.video_stream import VideoStreamer


# initialize ZeroMQ context and socket
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:6767")

# load the model
model = models.get(Models.YOLO_NAS_S, pretrained_weights="coco")

# Acquisition loop
with VideoStreamer(0) as stream:
    while True:
        img = stream.get_current_frame()
        if img is None: continue

        # detect objects in the image
        results = model.predict(img, fuse_model=False)
        # parse the results
        boxes = results.prediction.bboxes_xyxy
        label_names = results.class_names
        labels = results.prediction.labels
        confidence = results.prediction.confidence

        # small check if there are no detections
        if labels.size < 1:
            text = "No detections."
            response = {"text": text}

        else:
            # count the number of people
            num_people = sum([1 for o in labels if label_names[o] == "person"])

            # count the number of cats
            num_cats = sum([1 for o in labels if label_names[o] == "cat"])

            response = {
                "num_people": num_people,
                "num_cats": num_cats,
            }

        # send the json string over the socket
        json_response = json.dumps(response)
        socket.send_string(json_response)