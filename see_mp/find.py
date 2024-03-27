import json
import zmq
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer


# initialize zmq context and socket to send detection
context = zmq.Context()
socket = context.socket(zmq.PUB)
socket.bind("tcp://*:6767")

# load the model
model = models.get(Models.YOLO_NAS_S, pretrained_weights="coco")

# classes we care about
targets = ["person", "cat"]

# stream over the default camera
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
            response = {}
            # count the number of targets
            for targ in targets:
                count = sum([1 for l in labels if label_names[l] == targ])
                response[f"num_{targ}"] = count


        # send the json string over the socket
        json_response = json.dumps(response)
        socket.send_string(json_response)
