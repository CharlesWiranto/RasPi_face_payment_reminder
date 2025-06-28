import RPi.GPIO as GPIO
import time
import math

GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)

# Create PWM instance at 50Hz
pwm = GPIO.PWM(17, 50)
pwm.start(0)

def angle_to_duty(angle):
    """Convert angle (0-180) to duty cycle (2-12%)"""
    return angle / 18 + 2

def smooth_move(start_angle, end_angle, duration=1.0):
    """
    Smooth movement with easing function for more natural motion
    Uses quadratic easing in/out - accelerates then decelerates
    """
    steps = 60  # Increase for smoother motion
    delay = duration / steps
    
    for i in range(steps + 1):
        # Normalized progress (0 to 1)
        t = i / steps
        
        # Quadratic ease in/out function
        # This creates acceleration at start and deceleration at end
        if t < 0.5:
            ease_t = 2 * t * t
        else:
            ease_t = -1 + (4 - 2 * t) * t
        
        angle = start_angle + (end_angle - start_angle) * ease_t
        duty = angle_to_duty(angle)
        pwm.ChangeDutyCycle(duty)
        time.sleep(delay)

try:
    print("Servo sweeping smoothly between 0° and 180°")
    print("Press Ctrl+C to stop")
    
    while True:
        # Move from 0° to 180° with smooth acceleration/deceleration
        smooth_move(0, 180, 2.0)  # 2 seconds to move
        
        # Move from 180° back to 0° with smooth acceleration/deceleration
        smooth_move(180, 0, 2.0)   # 2 seconds to return
        
except KeyboardInterrupt:
    print("\nStopping servo")
    pwm.stop()
    GPIO.cleanup()