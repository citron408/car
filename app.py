from flask import Flask, render_template, request, jsonify
import threading
import time

# Use stub GPIO for development/testing (motor control will not physically run GPIO pins)
# On a real Raspberry Pi with GPIO, set `ENABLE_REAL_GPIO = True` and run with sudo
ENABLE_REAL_GPIO = True

if ENABLE_REAL_GPIO:
    try:
        import motor
        motor.init_gpio()
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

app = Flask(__name__, static_folder='static', template_folder='templates')

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


@app.route('/api/status', methods=['GET'])
def api_status():
    return jsonify({'action': current_action})


if __name__ == '__main__':
    # Disable Flask debug/reloader here so the process stays stable in production/dev shells.
    app.run(host='0.0.0.0', port=5000, debug=False, use_reloader=False)
