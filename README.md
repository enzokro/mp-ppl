# MP PPL Count

Counts how many people and cats are in a room.

There are two main setups:   

Client and server setup, meant for local testing:  
- `server.py` runs a small server that listens for detections and updates a webpage. 
- `client.py` runs and `POST`s detections to this local endpoint.  

Endpoint setup, meant for deployment:
- `endpoint.py` runs a video stream and detector loop. There is a `/detections` endpoint that returns the current detections.  

`VideoStreamer` is a threaded wrapper around OpenCV's VideoCapture, with an internal frame buffer.