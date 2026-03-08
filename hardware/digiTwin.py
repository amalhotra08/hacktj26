from flask import Flask, request, Response
import cv2
import numpy as np

app = Flask(__name__)

# This will hold the latest frame in memory for the live stream
latest_frame = None

@app.route('/upload', methods=['POST'])
def receive_image():
    global latest_frame
    if 'image' in request.files:
        # Read the incoming image file directly into memory
        file_bytes = np.frombuffer(request.files['image'].read(), np.uint8)
        img = cv2.imdecode(file_bytes, cv2.IMREAD_COLOR)
        
        # Re-encode it as JPEG for the web stream
        ret, buffer = cv2.imencode('.jpg', img)
        if ret:
            latest_frame = buffer.tobytes()
            
        return "Frame received", 200
    return "No image", 400

# This generator function creates the live video feed
def generate_frames():
    global latest_frame
    while True:
        if latest_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + latest_frame + b'\r\n')

# The route for the actual video player
@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')

# The homepage your teammates will open
@app.route('/')
def index():
    return '''
    <html>
        <head><title>AeroTwin Live Dashboard</title></head>
        <body style="background-color:#1e1e1e; color:white; text-align:center; font-family:sans-serif;">
            <h1>AeroTwin Live Sensor Feed</h1>
            <img src="/video_feed" width="1000" style="border: 3px solid #00ffcc; border-radius: 10px;">
        </body>
    </html>
    '''

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, threaded=True)