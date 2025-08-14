import paho.mqtt.client as paho
import pyfirmata
import time

# Constants
DEFAULT_SERVO_POS = 180
THRESHOLDS = {
    'fire': 0.5,
    'lpg': 0.5,
    'rain': 0.7,
    'light': 45
}
DEBOUNCE_DELAY = 0.1
MQTT_BROKER = '192.168.248.70'
MQTT_PORT = 1883

# Initialize Arduino board
try:
    board = pyfirmata.Arduino("/dev/ttyUSB1")
except:
    print("Failed to connect to Arduino")
    exit(1)

# Define pins
light = board.get_pin('d:2:o')
gate = board.get_pin('d:10:s')
fire = board.get_pin('a:3:i')
lpg = board.get_pin('a:2:i')
ld = board.get_pin('a:0:i')
ir = board.get_pin('d:13:i')
servo = board.get_pin('d:9:s')
rain = board.get_pin('a:1:i')
r = board.get_pin('d:6:p')
g = board.get_pin('d:5:p')
b = board.get_pin('d:11:p')
buzzer = board.get_pin('d:12:o')
servo2 = board.get_pin('d:3:s')
button = board.get_pin('d:8:i')

# Start PyFirmata iterator
it = pyfirmata.util.Iterator(board)
it.start()

# Initialize states
gate.write(DEFAULT_SERVO_POS)
servo2.write(DEFAULT_SERVO_POS)
led_state = False
prev_button_state = True
last_button_time = 0

# Initialize sensor variables
fire_status = lpg_status = rain_status = ld_status = None
ldper = 0
ir_status = True

def read_sensor(pin, default=None):
    """Safe sensor reading with default value"""
    try:
        value = pin.read()
        return value if value is not None else default
    except:
        return default

def handle_emergency():
    """Handle fire/LPG emergency situations"""
    if (read_sensor(fire, 1.0) < THRESHOLDS['fire'] or 
        read_sensor(lpg, 0.0) > THRESHOLDS['lpg']):
        servo.write(0)  # Close valve
        for _ in range(3):  # Triple beep pattern
            buzzer.write(1)
            time.sleep(0.25)
            buzzer.write(0)
            time.sleep(0.15)
        return True
    return False

def on_connect(client, userdata, flags, rc):
    """MQTT connection callback"""
    if rc == 0:
        print("Connected to MQTT Broker!")
        # Subscribe to topics
        client.subscribe('LK/Light')
        client.subscribe('LK/LPGR')
        client.subscribe('LK/Gate')
        client.subscribe('LK/CLOTHES')
        client.subscribe('LK/R')
        client.subscribe('LK/G')
        client.subscribe('LK/B')
    else:
        print(f"Failed to connect, return code {rc}")

def on_message_action(client, userdata, message):
    """MQTT message callback"""
    topic = message.topic
    msg = message.payload.decode("utf-8")

    if topic == 'LK/Light':
        if msg == 'ON':
            light.write(1)
        elif msg == 'OFF':
            light.write(0)
        elif msg == 'OPEN':
            light.write(1 if ldper < THRESHOLDS['light'] else 0)

    elif topic == 'LK/CLOTHES':
        if msg == 'OPEN':
            servo2.write(DEFAULT_SERVO_POS)
        elif msg == 'CLOSE':
            servo2.write(0)
        elif msg == 'ON':
            if rain_status is not None and ld_status is not None:
                if ldper < THRESHOLDS['light']:
                    servo2.write(0)
                elif rain_status < THRESHOLDS['rain']:
                    mqtt_client.publish('LK/RAIN', 'DETECTED')
                    servo2.write(0)
                else:
                    mqtt_client.publish('LK/RAIN', 'NOT DETECTED')
                    servo2.write(DEFAULT_SERVO_POS)

    elif topic == 'LK/Gate':
        if msg == 'OPEN':
            gate.write(90)
        elif msg == 'CLOSE':
            gate.write(DEFAULT_SERVO_POS)
        elif msg == 'ON':
            if read_sensor(ir, True) == False:
                gate.write(90)
                time.sleep(5)
                gate.write(DEFAULT_SERVO_POS)

    elif topic == 'LK/LPGR':
        if msg == 'OPEN':
            servo.write(100)
        elif msg == 'CLOSE':
            servo.write(0)
        elif msg == 'ON':
            if (read_sensor(fire, 1.0) < THRESHOLDS['fire'] or 
                read_sensor(lpg, 0.0) > THRESHOLDS['lpg']):
                servo.write(0)
            else:
                servo.write(100)

    # RGB LED control
    elif topic == 'LK/R':
        r_value = round(float(msg) / 255.0, 2)
        r.write(r_value)
    elif topic == 'LK/G':
        g_value = round(float(msg) / 255.0, 2)
        g.write(g_value)
    elif topic == 'LK/B':
        b_value = round(float(msg) / 255.0, 2)
        b.write(b_value)

# Initialize MQTT client
mqtt_client = paho.Client()
mqtt_client.on_connect = on_connect
mqtt_client.on_message = on_message_action

try:
    mqtt_client.connect(MQTT_BROKER, MQTT_PORT, keepalive=60)
    mqtt_client.loop_start()
except Exception as e:
    print(f"MQTT connection error: {e}")
    board.exit()
    exit(1)

# Main loop
try:
    while True:
        # Read all sensors
        fire_status = read_sensor(fire, 1.0)
        lpg_status = read_sensor(lpg, 0.0)
        ld_status = read_sensor(ld)
        rain_status = read_sensor(rain)
        ir_status = read_sensor(ir, True)
        
        if ld_status is not None:
            ldper = round(100 - (ld_status * 100), 2)
        
        # Handle button with debounce
        current_time = time.time()
        button_state = read_sensor(button, True)
        if (button_state is False and 
            prev_button_state is True and 
            (current_time - last_button_time) > DEBOUNCE_DELAY):
            led_state = not led_state
            light.write(led_state)
            last_button_time = current_time
        prev_button_state = button_state
        
        # Check emergency
        handle_emergency()
        
        # Publish status updates
        mqtt_client.publish('LK/Fire', 'False' if fire_status < THRESHOLDS['fire'] else 'True')
        mqtt_client.publish('LK/Lpg', 'False' if lpg_status > THRESHOLDS['lpg'] else 'True')
        mqtt_client.publish('LK/Ld', ldper)
        mqtt_client.publish('LK/LightR', light.read())
        mqtt_client.publish('LK/GateR', gate.read())
        mqtt_client.publish('LK/Theif', ir_status)
        mqtt_client.publish('LK/LPGv', servo.read())
        
        time.sleep(0.1)

except KeyboardInterrupt:
    print("Exiting Program...")
    mqtt_client.loop_stop()
    board.exit()
except Exception as e:
    print(f"Error: {e}")
    mqtt_client.loop_stop()
    board.exit()