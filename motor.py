import time
import RPi.GPIO as GPIO

# Configuration (tiny and obvious)
PWM_R = 27
DIR_R = 17
PWM_L = 5
DIR_L = 6
# Defer GPIO setup to initialization function to avoid failures at import time
_gpio_initialized = False

def init_gpio():
    global _gpio_initialized
    if _gpio_initialized:
        return
    try:
        GPIO.setmode(GPIO.BCM)
        GPIO.setup(PWM_R, GPIO.OUT)
        GPIO.setup(DIR_R, GPIO.OUT)
        GPIO.setup(PWM_L, GPIO.OUT)
        GPIO.setup(DIR_L, GPIO.OUT)

        GPIO.output(DIR_R, GPIO.LOW)
        GPIO.output(PWM_R, GPIO.LOW)
        GPIO.output(DIR_L, GPIO.LOW)
        GPIO.output(PWM_L, GPIO.LOW)
        _gpio_initialized = True
    except Exception as e:
        print(f"Warning: GPIO initialization failed: {e}")


def forward(timeInSeconds: int):
  GPIO.output(DIR_R, GPIO.HIGH)
  GPIO.output(DIR_L, GPIO.HIGH)
  GPIO.output(PWM_R, GPIO.HIGH)
  GPIO.output(PWM_L, GPIO.HIGH)
  time.sleep(timeInSeconds)
  GPIO.output(PWM_R, GPIO.LOW)
  GPIO.output(PWM_L, GPIO.LOW)

def backward(timeInSeconds: int):
  GPIO.output(DIR_R, GPIO.LOW)
  GPIO.output(DIR_L, GPIO.LOW)
  GPIO.output(PWM_R, GPIO.HIGH)
  GPIO.output(PWM_L, GPIO.HIGH)
  time.sleep(timeInSeconds)
  GPIO.output(PWM_R, GPIO.LOW)
  GPIO.output(PWM_L, GPIO.LOW)
  
def stop():
  GPIO.output(PWM_R, GPIO.LOW)
  GPIO.output(PWM_L, GPIO.LOW)

def turnRight(timeInSeconds: int):
  GPIO.output(DIR_R, GPIO.LOW)
  GPIO.output(DIR_L, GPIO.HIGH)
  GPIO.output(PWM_R, GPIO.HIGH)
  GPIO.output(PWM_L, GPIO.HIGH)
  time.sleep(timeInSeconds)
  GPIO.output(PWM_R, GPIO.LOW)
  GPIO.output(PWM_L, GPIO.LOW)
# try:
#   init_gpio()
#   forward(2)
#   turnRight(5)
#   stop()	
#   time.sleep(1)
#   backward(4)
 
# finally:
# 	GPIO.output(DIR_R, GPIO.LOW)
# 	GPIO.output(PWM_R, GPIO.LOW)
# 	GPIO.output(DIR_L, GPIO.LOW)
# 	GPIO.output(PWM_L, GPIO.LOW)
# 	GPIO.cleanup()