import cv2
import numpy as np
import threading
import logging
from typing import Optional, Union, List

logger = logging.getLogger(__name__)

class VideoStreamer:
    """
    Continuously reads frames from a video capture source.
    """
    class Break(Exception):
        """
        Custom exception to break out of the video capture loop.
        """
        pass

    def __init__(self, video_source: Union[str, int], frame_buffer_size: int = 10):
        """
        Initializes a video stream with a frame buffer.

        Args:
            video_source (str): The video source, either a file path or a camera index.
            frame_buffer_size (int): The size of the frame buffer (default: 10).
        """
        # camera/video source to be read
        self.video_source = video_source
        self.cap = None

        # frame and buffer setup
        self.current_frame = None
        self.frame_buffer_size = frame_buffer_size
        self.frame_buffer = []

        # read frames from a thread
        self.thread = None
        self.stop_event = threading.Event()

    def start(self):
        """
        Start capturing video frames in a background thread.
        """
        # setup the camera
        self.cap = cv2.VideoCapture(self.video_source)
        if not self.cap.isOpened():
            logger.error(f"Failed to open video source: {self.video_source}")
            raise ValueError(f"Failed to open video source: {self.video_source}")

        # read frames in the background
        self.thread = threading.Thread(target=self._read_frames, daemon=True)
        self.thread.start()
        logger.info(f"Started video capture from source: {self.video_source}")

    def _read_frames(self):
        """
        Reads frames until signalled to stop. 
        """
        while not self.stop_event.is_set():
            ret, frame = self.cap.read()
            if ret:
                self.current_frame = frame
                # buffer management
                if len(self.frame_buffer) >= self.frame_buffer_size:
                    self.frame_buffer.pop(0)
                self.frame_buffer.append(frame)
            else:
                logger.warning(f"Failed to read frame from video source: {self.video_source}")
                break

    def get_current_frame(self) -> Optional[np.ndarray]:
        """
        Get the current frame from the video capture.

        Returns:
            Optional[np.ndarray]: The current frame as a NumPy array, or None if no frame is available.
        """
        return self.current_frame

    def get_frame_buffer(self) -> List[np.ndarray]:
        """
        Get the frame buffer containing the most recent frames.

        Returns:
            list: The frame buffer as a list of NumPy arrays.
        """
        return self.frame_buffer

    def stop(self):
        """
        Stop the video capture and release resources.
        """
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join()
        if self.cap:
            self.cap.release()
        logger.info(f"Stopped video capture from source: {self.video_source}")

    def __enter__(self):
        """
        Context manager entry point.
        """
        self.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback):
        """
        Context manager exit point.
        """
        self.stop()

    def __del__(self):
        """
        Destructor to ensure resources are released.
        """
        self.stop()