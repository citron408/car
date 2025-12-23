import RPi.GPIO as GPIO

# LED pin configuration
LED = 22

# Track whether LED GPIO was initialized to avoid repeated setup
_gpio_initialized = False
LED_STATE = False

def init_gpio():
    global _gpio_initialized, LED_STATE
    if _gpio_initialized:
        return
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(LED, GPIO.OUT)
        GPIO.output(LED, GPIO.LOW)
        LED_STATE = False
        _gpio_initialized = True
    except Exception as e:
        print(f"Warning: LED GPIO initialization failed: {e}")

def turnOnLed():
    GPIO.output(LED, GPIO.HIGH)
    global LED_STATE
    LED_STATE = True

def turnOffLed():
    GPIO.output(LED, GPIO.LOW)
    global LED_STATE
    LED_STATE = False

def toggleLed():
    global LED_STATE
    if LED_STATE:
        turnOffLed()
    else:
        turnOnLed()
    return LED_STATE
