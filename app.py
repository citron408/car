from flask import Flask, Response, render_template, request, jsonify
import threading
import time

try:
    import cv2
    import numpy as np
    from picamera2 import MappedArray, Picamera2
    from picamera2.devices import IMX500
    from picamera2.devices.imx500 import NetworkIntrinsics, postprocess_nanodet_detection
    CAMERA_IMPORTS_OK = True
except Exception:
    CAMERA_IMPORTS_OK = False

# Use stub GPIO for development/testing (motor control will not physically run GPIO pins)
# On a real Raspberry Pi with GPIO, set `ENABLE_REAL_GPIO = True` and run with sudo
ENABLE_REAL_GPIO = True
led_module = None

if ENABLE_REAL_GPIO:
    try:
        import motor
        import led
        motor.init_gpio()
        try:
            led.init_gpio()
        except Exception:
            pass
        led_module = led
    except Exception as e:
        print(f"Warning: motor module import/init failed: {e}")
        ENABLE_REAL_GPIO = False

if not ENABLE_REAL_GPIO:
    # Create a stub so the web UI can still run for development
    class _DummyGPIO:
        BCM = None
        OUT = None
        HIGH = 1
        LOW = 0
        def setmode(self, *a, **k):
            pass
        def setup(self, *a, **k):
            pass
        def output(self, *a, **k):
            pass
        def cleanup(self, *a, **k):
            pass
    motor = type('motor_stub', (), {})()
    motor.GPIO = _DummyGPIO()
    motor.PWM_R = 27
    motor.PWM_L = 5
    motor.DIR_R = 17
    motor.DIR_L = 6
    motor.LED = 22
    # led stub
    led_mod = type('led_stub', (), {})()
    led_mod._led_state = False
    def _led_on():
        motor.GPIO.output(motor.LED, motor.GPIO.HIGH)
        led_mod._led_state = True
    def _led_off():
        motor.GPIO.output(motor.LED, motor.GPIO.LOW)
        led_mod._led_state = False
    def _led_toggle():
        if led_mod._led_state:
            _led_off()
        else:
            _led_on()
        return led_mod._led_state
    led_mod.turnOnLed = _led_on
    led_mod.turnOffLed = _led_off
    led_mod.toggleLed = _led_toggle
    led_module = led_mod

app = Flask(__name__, static_folder='static', template_folder='templates')


class CameraService:
    def __init__(self):
        self._lock = threading.Lock()
        self._thread = None
        self._stop_event = threading.Event()
        self._latest_jpeg = None
        self._latest_detections = []
        self._running = False
        self._error = None

    def _labels(self):
        labels = self.intrinsics.labels or []
        if getattr(self.intrinsics, 'ignore_dash_labels', False):
            labels = [label for label in labels if label and label != '-']
        return labels

    def _parse_detections(self, metadata):
        np_outputs = self.imx500.get_outputs(metadata, add_batch=True)
        input_w, input_h = self.imx500.get_input_size()
        if np_outputs is None:
            return []

        threshold = float(getattr(self.intrinsics, 'threshold', 0.55))
        iou = float(getattr(self.intrinsics, 'iou', 0.65))
        max_detections = int(getattr(self.intrinsics, 'max_detections', 10))

        if self.intrinsics.postprocess == 'nanodet':
            boxes, scores, classes = postprocess_nanodet_detection(
                outputs=np_outputs[0],
                conf=threshold,
                iou_thres=iou,
                max_out_dets=max_detections,
            )[0]
            from picamera2.devices.imx500.postprocess import scale_boxes
            boxes = scale_boxes(boxes, 1, 1, input_h, input_w, False, False)
        else:
            boxes, scores, classes = np_outputs[0][0], np_outputs[1][0], np_outputs[2][0]
            if getattr(self.intrinsics, 'bbox_normalization', False):
                boxes = boxes / input_h
            boxes = np.array_split(boxes, 4, axis=1)
            boxes = list(zip(*boxes))

        detections = []
        labels = self._labels()
        for box, score, category in zip(boxes, scores, classes):
            if score <= threshold:
                continue
            x, y, w, h = self.imx500.convert_inference_coords(box, metadata, self.picam2)
            category_idx = int(category)
            label = labels[category_idx] if 0 <= category_idx < len(labels) else str(category_idx)
            detections.append({
                'label': label,
                'confidence': float(score),
                'box': [int(x), int(y), int(w), int(h)],
            })
        return detections

    def _run(self):
        model_path = '/usr/share/imx500-models/imx500_network_ssd_mobilenetv2_fpnlite_320x320_pp.rpk'
        try:
            self.imx500 = IMX500(model_path)
            self.intrinsics = self.imx500.network_intrinsics
            if not self.intrinsics:
                self.intrinsics = NetworkIntrinsics()
                self.intrinsics.task = 'object detection'
            if self.intrinsics.task != 'object detection':
                raise RuntimeError('IMX500 model is not an object detection task')

            if self.intrinsics.labels is None:
                # Fallback to generic labels when the demo labels file is not available locally.
                try:
                    with open('assets/coco_labels.txt', 'r') as f:
                        self.intrinsics.labels = f.read().splitlines()
                except Exception:
                    self.intrinsics.labels = [str(i) for i in range(1000)]
            self.intrinsics.update_with_defaults()

            self.picam2 = Picamera2(self.imx500.camera_num)
            config = self.picam2.create_preview_configuration(
                {'format': 'RGB888'},
                controls={'FrameRate': self.intrinsics.inference_rate},
                buffer_count=6,
            )
            self.imx500.show_network_fw_progress_bar()
            self.picam2.start(config, show_preview=False)
            if getattr(self.intrinsics, 'preserve_aspect_ratio', False):
                self.imx500.set_auto_aspect_ratio()

            self._running = True

            while not self._stop_event.is_set():
                request = self.picam2.capture_request()
                metadata = request.get_metadata() or {}
                detections = self._parse_detections(metadata)

                with MappedArray(request, 'main') as m:
                    for det in detections:
                        x, y, w, h = det['box']
                        label = f"{det['label']} ({det['confidence']:.2f})"
                        cv2.rectangle(m.array, (x, y), (x + w, y + h), (0, 255, 0), thickness=2)
                        cv2.putText(
                            m.array,
                            label,
                            (x + 5, max(12, y - 4)),
                            cv2.FONT_HERSHEY_SIMPLEX,
                            0.45,
                            (0, 0, 255),
                            1,
                        )

                    ok, encoded = cv2.imencode('.jpg', cv2.cvtColor(m.array, cv2.COLOR_RGB2BGR))
                    if ok:
                        with self._lock:
                            self._latest_jpeg = encoded.tobytes()
                            self._latest_detections = detections

                request.release()

        except Exception as e:
            self._error = str(e)
        finally:
            try:
                self.picam2.stop()
            except Exception:
                pass
            self._running = False

    def start(self):
        if not CAMERA_IMPORTS_OK:
            self._error = 'camera dependencies are not available'
            return False

        if self._thread and self._thread.is_alive():
            return True

        self._stop_event.clear()
        self._error = None
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        return True

    def stop(self):
        self._stop_event.set()

    def frame(self):
        with self._lock:
            return self._latest_jpeg

    def detections(self):
        with self._lock:
            return list(self._latest_detections)

    def status(self):
        return {
            'running': self._running,
            'error': self._error,
            'has_frame': self.frame() is not None,
            'detections': self.detections(),
        }


camera_service = CameraService()
camera_service.start()

# Threading control
stop_event = threading.Event()
action_lock = threading.Lock()
current_thread = None
current_action = None

def _set_pwm_high():
    motor.GPIO.output(motor.PWM_R, motor.GPIO.HIGH)
    motor.GPIO.output(motor.PWM_L, motor.GPIO.HIGH)

def _set_pwm_low():
    motor.GPIO.output(motor.PWM_R, motor.GPIO.LOW)
    motor.GPIO.output(motor.PWM_L, motor.GPIO.LOW)

def _run(action: str):
    global current_action
    stop_event.clear()
    current_action = action
    try:
        if action == 'forward':
            motor.GPIO.output(motor.DIR_R, motor.GPIO.HIGH)
            motor.GPIO.output(motor.DIR_L, motor.GPIO.HIGH)
        elif action == 'backward':
            motor.GPIO.output(motor.DIR_R, motor.GPIO.LOW)
            motor.GPIO.output(motor.DIR_L, motor.GPIO.LOW)
        elif action == 'turnRight':
            motor.GPIO.output(motor.DIR_R, motor.GPIO.LOW)
            motor.GPIO.output(motor.DIR_L, motor.GPIO.HIGH)
        elif action == 'left':
            motor.GPIO.output(motor.DIR_R, motor.GPIO.HIGH)
            motor.GPIO.output(motor.DIR_L, motor.GPIO.LOW)

        _set_pwm_high()

        while not stop_event.is_set():
            time.sleep(0.05)

        _set_pwm_low()
    finally:
        current_action = None

def start_action(action: str):
    global current_thread
    with action_lock:
        if current_thread and current_thread.is_alive():
            return False, 'another action is running'
        t = threading.Thread(target=_run, args=(action,), daemon=True)
        current_thread = t
        t.start()
        return True, 'started'


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/<action>', methods=['POST'])
def api_action(action):
    if action not in ('forward', 'backward', 'turnRight', 'left'):
        return jsonify({'error': 'invalid action'}), 400

    ok, msg = start_action(action)
    if ok:
        return jsonify({'status': 'started', 'action': action})
    else:
        return jsonify({'status': 'busy', 'message': msg}), 409


@app.route('/api/stop', methods=['POST'])
def api_stop():
    stop_event.set()
    try:
        motor.GPIO.output(motor.PWM_R, motor.GPIO.LOW)
        motor.GPIO.output(motor.PWM_L, motor.GPIO.LOW)
    except Exception:
        pass
    return jsonify({'status': 'stopped'})


@app.route('/api/led', methods=['POST'])
def api_led():
    try:
        new_state = led_module.toggleLed()
        return jsonify({'led': 'on' if new_state else 'off'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({'action': current_action})


@app.route('/camera/stream', methods=['GET'])
def camera_stream():
    if not camera_service.start():
        return jsonify({'error': camera_service.status()['error']}), 503

    def generate():
        while True:
            frame = camera_service.frame()
            if frame is None:
                time.sleep(0.05)
                continue
            yield (
                b'--frame\r\n'
                b'Content-Type: image/jpeg\r\n\r\n' + frame + b'\r\n'
            )

    return Response(generate(), mimetype='multipart/x-mixed-replace; boundary=frame')


@app.route('/api/camera/status', methods=['GET'])
def api_camera_status():
    status = camera_service.status()
    code = 200 if status['error'] is None else 503
    return jsonify(status), code


if __name__ == '__main__':
    # Disable Flask debug/reloader here so the process stays stable in production/dev shells.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
