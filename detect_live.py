from super_gradients.training import models
from super_gradients.common.object_names import Models
from chaski.dets.video_stream import VideoStreamer
import cv2

model = models.get(Models.YOLO_NAS_S, pretrained_weights="coco")

# Acquisition loop
with VideoStreamer(0) as stream:
    while True:
        img = stream.get_current_frame()
        if img is None: continue

        # detect objects in the image
        output_image = img.copy()
        results = model.predict(img, fuse_model=False)
        # parse the results
        boxes = results.prediction.bboxes_xyxy
        label_names = results.class_names
        labels = results.prediction.labels
        confidence = results.prediction.confidence

        # small check if there are no detections
        if labels.size < 1:
            text = "No detections on CPU"
            print(text)

        else:
            # count the number of people
            num_people = sum([1 for l in labels if l == "person"])

            # count the number of cats
            num_cats = sum([1 for l in labels if l == "cat"])

            
            count = -1
            for lab in labels:
                count += 1
                # Extract info
                local_label = label_names[labels[count]]
                local_conf = confidence[count]
                label = f"{local_label} ({local_conf:.2f})"
                x1 = boxes[count, 0]
                y1 = boxes[count, 1]
                x2 = boxes[count, 2]
                y2 = boxes[count, 3]
                x1, y1, x2, y2 = int(x1), int(y1), int(x2), int(y2)  # convert to int values
                # Paint bboxes
                output_image = cv2.rectangle(output_image, (x1, y1), (x2, y2), (255, 0, 0), 2)
                output_image = cv2.putText(output_image, label, (x1 - 10, y1 - 10),
                                        cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

        cv2.imshow("Results", output_image)
        if cv2.waitKey(1) == ord('q'):
            raise stream.Break
