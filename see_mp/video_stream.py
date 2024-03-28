import cv2
import numpy as np
import threading
import logging
from typing import Optional, Union, List, Dict

logger = logging.getLogger(__name__)

class VideoStreamer:
    "Continuously reads frames from a video capture source."
    
    class Break(Exception):
        "Custom exception to break out of the video capture loop."
        pass
    
    def __init__(self, video_source: Union[str, int], frame_buffer_size: int = 10, capture_props: Optional[Dict[str, Union[int, float]]] = None):
        "Initializes a video stream with a frame buffer and optional capture properties."
        
        # camera and buffer settings
        self.video_source = video_source
        self.capture_props = capture_props or {}
        self.cap = None

        # buffer settings
        self.frame_buffer_size = frame_buffer_size
        self.current_frame = None
        self.frame_buffer = []

        # handles thread in the background
        self.thread = None
        self.stop_event = threading.Event()
    
    def start(self):
        "Start capturing video frames in a background thread."
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video source: {self.video_source}")
            raise ValueError(f"Failed to open video source: {self.video_source}")
        # setup and start camera
        self._set_capture_props()
        self._start_frame_thread()
    
    def _set_capture_props(self):
        "Set the video capture properties based on the provided configuration."
        for prop, value in self.capture_props.items():
            self.cap.set(getattr(cv2, prop), value)
        # view some info about the opened camera
        fps = int(self.cap.get(cv2.CAP_PROP_FPS))
        logger.info(f"Video source opened with FPS: {fps}")
    
    def _start_frame_thread(self):
        "Start the background thread for reading frames."
        self.thread = threading.Thread(target=self._read_frames)
        self.thread.start()
        logger.info(f"Started video capture from source: {self.video_source}")
    
    def _read_frames(self):
        "Reads frames until signalled to stop."
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                self._update_frame_buffer(frame)
            else:
                logger.warning(f"Failed to read frame from video source: {self.video_source}")
                break
    
    def _update_frame_buffer(self, frame):
        "Updates the frame buffer with the latest frame."
        if len(self.frame_buffer) >= self.frame_buffer_size:
            self.frame_buffer.pop(0)
        self.frame_buffer.append(frame)
    
    def get_current_frame(self) -> Optional[np.ndarray]:
        "Get the current frame from the video capture."
        return self.current_frame
    
    def get_frame_buffer(self) -> List[np.ndarray]:
        "Get the frame buffer containing the most recent frames."
        return self.frame_buffer
    
    def stop(self):
        "Stop the video capture and release resources."
        self.stop_event.set()
        self._join_frame_thread()
        self._release_capture()
        logger.info(f"Stopped video capture from source: {self.video_source}")
    
    def _join_frame_thread(self):
        "Wait for the frame reading thread to finish."
        if self.thread and self.thread.is_alive():
            self.thread.join()
    
    def _release_capture(self):
        "Release the video capture resources."
        if self.cap:
            self.cap.release()
    
    def __enter__(self):
        "Context manager entry point."
        self.start()
        return self
    
    def __exit__(self, exc_type, exc_value, traceback):
        "Context manager exit point."
        self.stop()
    
    def __del__(self):
        "Destructor to ensure resources are released."
        self.stop()