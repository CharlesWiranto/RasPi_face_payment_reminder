import RPi.GPIO as GPIO
import time
import math
from flask import Flask, request, jsonify
import threading

app = Flask(__name__)

# GPIO Setup - use different pins for horizontal and vertical servos
HORIZONTAL_PIN = 17  # Your original pin
VERTICAL_PIN = 27    # New pin for vertical servo

# Initialize both servos
GPIO.setmode(GPIO.BCM)
GPIO.setup(HORIZONTAL_PIN, GPIO.OUT)
GPIO.setup(VERTICAL_PIN, GPIO.OUT)
pwm_h = GPIO.PWM(HORIZONTAL_PIN, 50)  # 50Hz frequency
pwm_v = GPIO.PWM(VERTICAL_PIN, 50)    # 50Hz frequency
pwm_h.start(0)
pwm_v.start(0)

# Movement control variables
is_looping = False
loop_thread = None
current_angle_h = 90  # Horizontal position
current_angle_v = 90  # Vertical position

def angle_to_duty(angle):
    """Convert angle to duty cycle (2%-12%)"""
    return angle / 18 + 2

def quintic_easing(t):
    """Quintic easing function for ultra-smooth motion"""
    return t * t * t * (t * (t * 6 - 15) + 10)

def smooth_move(pwm_obj, current_angle, start, end, duration=2.0):
    """Generic smooth movement function for any servo"""
    steps = max(30, int(duration * 30))
    delay = duration / steps
    
    for i in range(steps + 1):
        t = i / steps
        eased_t = quintic_easing(t)
        current_angle = start + (end - start) * eased_t
        pwm_obj.ChangeDutyCycle(angle_to_duty(current_angle))
        time.sleep(delay)
    return current_angle  # Return the new angle

def set_angle(pwm_obj, current_angle, angle, duration=0.5):
    """Generic angle setting for any servo"""
    if duration <= 0:
        # Immediate movement
        pwm_obj.ChangeDutyCycle(angle_to_duty(angle))
        time.sleep(0.3)  # Give servo time to reach position
        return angle
    else:
        # Smooth movement
        return smooth_move(pwm_obj, current_angle, current_angle, angle, duration)

# Vertical servo specific endpoints
@app.route('/api/servo/vertical/set_angle', methods=['POST'])
def set_vertical_angle():
    global current_angle_v
    try:
        data = request.get_json()
        angle = data.get('angle', 90)
        duration = data.get('duration', 1.0)  # Slower default for vertical
        
        # Vertical servos often have limited range (adjust as needed)
        if not (30 <= angle <= 150):
            return jsonify({"error": "Vertical angle must be between 30 and 150 degrees"}), 400
        
        current_angle_v = set_angle(pwm_v, current_angle_v, angle, duration)
        pwm_v.ChangeDutyCycle(0)  # Stop sending pulses but maintain position
        return jsonify({
            "status": "success",
            "message": f"Vertical servo set to {angle}°",
            "current_angle": angle
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# Horizontal servo endpoints (modified from your original)
@app.route('/api/servo/horizontal/set_angle', methods=['POST'])
def set_horizontal_angle():
    global current_angle_h
    try:
        data = request.get_json()
        angle = data.get('angle', 90)
        duration = data.get('duration', 0.5)
        
        if not (0 <= angle <= 180):
            return jsonify({"error": "Angle must be between 0 and 180 degrees"}), 400
        
        current_angle_h = set_angle(pwm_h, current_angle_h, angle, duration)
        pwm_h.ChangeDutyCycle(0)
        return jsonify({
            "status": "success",
            "message": f"Horizontal servo set to {angle}°",
            "current_angle": angle
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500
def continuous_loop(duration=2.0):
    """Continuous back-and-forth movement"""
    global is_looping
    while is_looping:
        smooth_move(0, 180, duration/2)
        smooth_move(180, 0, duration/2)

# API Endpoints
@app.route('/api/servo/start_loop', methods=['POST'])
def start_loop():
    global is_looping, loop_thread
    
    try:
        if is_looping:
            return jsonify({"status": "error", "message": "Loop already running"}), 400
            
        duration = request.json.get('duration', 2.0)
        is_looping = True
        loop_thread = threading.Thread(target=continuous_loop, args=(duration,))
        loop_thread.start()
        
        return jsonify({
            "status": "success",
            "message": f"Started continuous loop with {duration}s cycle",
            "duration": duration
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servo/stop_loop', methods=['POST'])
def stop_loop():
    global is_looping, loop_thread
    
    try:
        if not is_looping:
            return jsonify({"status": "error", "message": "No loop running"}), 400
            
        is_looping = False
        if loop_thread:
            loop_thread.join()
        
        return jsonify({
            "status": "success",
            "message": "Stopped continuous loop"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servo/move', methods=['POST'])
def move_servo():
    try:
        if is_looping:
            return jsonify({"error": "Cannot move while looping is active"}), 400
            
        data = request.get_json()
        start_angle = data.get('start_angle', 0)
        end_angle = data.get('end_angle', 180)
        duration = data.get('duration', 2.0)
        
        if not (0 <= start_angle <= 180) or not (0 <= end_angle <= 180):
            return jsonify({"error": "Angles must be between 0 and 180 degrees"}), 400
        
        smooth_move(start_angle, end_angle, duration)
        return jsonify({
            "status": "success",
            "message": f"Servo moved from {start_angle}° to {end_angle}°",
            "duration": duration
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servo/set_angle', methods=['POST'])
def servo_set_angle():
    try:
        if is_looping:
            return jsonify({"error": "Cannot set angle while looping is active"}), 400
            
        data = request.get_json()
        angle = data.get('angle', 90)
        duration = data.get('duration', 0.5)  # Default 0.5s movement
        
        if not (0 <= angle <= 180):
            return jsonify({"error": "Angle must be between 0 and 180 degrees"}), 400
        
        set_angle(angle, duration)
        return jsonify({
            "status": "success",
            "message": f"Servo set to {angle}°",
            "current_angle": angle,
            "duration": duration
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/servo/stop', methods=['POST'])
def stop_servo():
    global is_looping
    try:
        is_looping = False
        pwm.ChangeDutyCycle(0)  # Stop sending pulses
        return jsonify({"status": "success", "message": "Servo stopped"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

def cleanup():
    pwm_h.stop()
    pwm_v.stop()
    GPIO.cleanup()

if __name__ == '__main__':
    try:
        print("Servo control server started. Endpoints available:")
        print("- POST /api/servo/set_angle")
        print("- POST /api/servo/start_loop")
        print("- POST /api/servo/stop_loop")
        print("- POST /api/servo/move")
        print("- POST /api/servo/stop")
        app.run(host='0.0.0.0', port=5000)
    except KeyboardInterrupt:
        print("\nStopping server...")
        is_looping = False
        cleanup()