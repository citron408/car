import time
import RPi.GPIO as GPIO

# Configuration (tiny and obvious)
PIN = 2        # BCM pin where the LED is connected
INTERVAL = 10 # seconds LED stays on and off

GPIO.setmode(GPIO.BCM)
GPIO.setup(PIN, GPIO.OUT)

try:
	while True:
		GPIO.output(PIN, GPIO.HIGH)
		time.sleep(INTERVAL)
		GPIO.output(PIN, GPIO.LOW)
		time.sleep(INTERVAL)
except KeyboardInterrupt:
	# Stop on Ctrl-C
	pass
finally:
	GPIO.output(PIN, GPIO.LOW)
	GPIO.cleanup()
