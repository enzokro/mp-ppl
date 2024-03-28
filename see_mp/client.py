import os
import requests
import fire
import cv2
from super_gradients.training import models
from super_gradients.common.object_names import Models
from see_mp.video_stream import VideoStreamer
from see_mp.utils import DetectionManager, draw_bounding_boxes, Config, parse_det_results


def main(
        draw: bool = False,
):
    # Load the detection model
    model = models.get(Config.MODEL_NAME, pretrained_weights="coco")

    # Detection manager
    detection_manager = DetectionManager(Config.TARGETS, Config.NUM_VALID_FRAMES, Config.THRESHOLD)

    # Stream over the default camera
    with VideoStreamer(0, capture_props=Config.CAP_PROPS) as stream:
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
                        response = requests.post(Config.DETECTION_URL, json=counts)
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