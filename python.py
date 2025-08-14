import paho.mqtt.client as paho  # Import paho MQTT library
import pyfirmata
import time

board = pyfirmata.Arduino("/dev/ttyUSB1")

# Define pins
light = board.get_pin('d:2:o')
gate = board.get_pin('d:10:s')
fire = board.get_pin('a:3:i')
lpg = board.get_pin('a:2:i')
ld = board.get_pin('a:0:i')
ir = board.get_pin('d:13:i')
servo = board.get_pin('d:9:s')
rain = board.get_pin('a:1:i')
r = board.get_pin('d:6:p')  # Red LED on PWM pin
g = board.get_pin('d:5:p')  # Green LED on PWM pin
b = board.get_pin('d:11:p')
buzzer = board.get_pin('d:12:o')
servo2 = board.get_pin('d:3:s')
button = board.get_pin('d:8:i')# Blue LED on PWM pin

# Start PyFirmata iterator to read input pins
it = pyfirmata.util.Iterator(board)
it.start()

gate.write(180)
servo2.write(180)
led_state = False
prev_button_state = True
# MQTT on_message callback
def on_message_action(client, userdata, message):  # This function will be called on receiving messages
    topic = message.topic  # Store topic
    msg = message.payload.decode("utf-8")  # Decode the message

    # Light control
    if topic == 'LK/Light':
        if msg == 'ON':
            light.write(1)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'OFF':
            light.write(0)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'OPEN':
            if ldper < 45:
                light.write(1)
            else:
                light.write(0)
    if topic == 'LK/CLOTHES':
        if msg == 'OPEN':
            servo2.write(180)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'CLOSE':
            servo2.write(0)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'ON':
            if rain_status is not None and ld_status is not None:
                if ldper < 45:
                    servo2.write(0)
                elif rain_status<0.7:
                    mqtt_client.publish('LK/RAIN', 'DETECTED')
                    servo2.write(0)
                else:
                    mqtt_client.publish('LK/RAIN', 'NOT DETECTED')
                    servo2.write(180)
            
    if topic == 'LK/Gate':
        if msg == 'OPEN':
            gate.write(90)
            print('Topic:', topic)
            print('Message:', msg)# Open gate (set servo to 90 degrees)
        elif msg == 'CLOSE':
            gate.write(180)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'ON':
            if ir_status == False:
                gate.write(90)
                time.sleep(5)
                gate.write(180)
            # Close gate (set servo to 0 degrees)

    # RGB LED control via sliders
    if topic == 'LK/R':  # Red LED
        r_value = round(float(msg) / 255.0,2)  # Normalize slider value (0-255) to PWM (0-1)
        r.write(r_value)
        print('Topic:', topic)
        print('Message:', msg)
    elif topic == 'LK/G':  # Green LED
        g_value = round(float(msg) / 255.0,2)
        g.write(g_value)
        print('Topic:', topic)
        print('Message:', msg)
    elif topic == 'LK/B':  # Blue LED
        b_value = round(float(msg) / 255.0,2)
        b.write(b_value)
        print('Topic:', topic)
        print('Message:', msg)
    if topic == 'LK/LPGR':
        if msg == 'OPEN':
            servo.write(100)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'CLOSE':
            servo.write(0)
            print('Topic:', topic)
            print('Message:', msg)
        elif msg == 'ON':
            if fire_status < 0.5 or lpg_status > 0.5:
                servo.write(0)
                
            else:
                servo.write(100)
                
            
            


# Initialize MQTT client
mqtt_client = paho.Client()  # Create paho client object
mqtt_client.connect('192.168.248.70', 1883)  # Connect to MQTT broker (replace IP with your broker's IP)
mqtt_client.loop_start()  # Start MQTT client thread
mqtt_client.on_message = on_message_action  # Link callback function for incoming messages

# Subscribe to topics
mqtt_client.subscribe('LK/Light')
mqtt_client.subscribe('LK/LPGR')
mqtt_client.subscribe('LK/Gate')
mqtt_client.subscribe('LK/CLOTHES')
mqtt_client.subscribe('LK/R')  # For Red LED slider
mqtt_client.subscribe('LK/G')  # For Green LED slider
mqtt_client.subscribe('LK/B')  # For Blue LED slider

# Continuous sensor monitoring and publishing
try:
    while True:
        time.sleep(0.2)
        fire_status = fire.read()
        if fire_status is not None:
            if fire_status < 0.5:
                mqtt_client.publish('LK/Fire', 'False')
            else:
                mqtt_client.publish('LK/Fire', 'True')
            

        lpg_status = lpg.read()
        if lpg_status is not None:
            if lpg_status > 0.5:
                mqtt_client.publish('LK/Lpg', 'False')
            else:
                mqtt_client.publish('LK/Lpg', 'True')
        if lpg_status is not None:
            if fire_status < 0.5 or lpg_status > 0.5:
                buzzer.write(1)
                time.sleep(0.25)
                buzzer.write(0)
                time.sleep(0.15)
            else:
                buzzer.write(0)
        
            
        
        
        ld_status = ld.read()
        
        if ld_status is not None:
            ldper = round(100 - (ld_status * 100), 2)# Convert to percentage
            mqtt_client.publish('LK/Ld', ldper)

        led_status = light.read()
        mqtt_client.publish('LK/LightR', led_status)

        servo_status = gate.read()
        mqtt_client.publish('LK/GateR', servo_status)

        ir_status = ir.read()
        if ir_status is not None:
             mqtt_client.publish('LK/Theif', ir_status)
        # Fire and LPG emergency actions
       

        lpg_valve = servo.read()
        mqtt_client.publish('LK/LPGv', lpg_valve)

        # Rain detection
        rain_status = rain.read()
        
        button_state=button.read()
        if button_state is False and prev_button_state is True:
            led_state = not led_state# Button pressed (LOW due to pull-up)
            light.write(led_state)
        prev_button_state = button_state
        print (rain_status)
        time.sleep(0.2)
    
    
        pass
          # Short delay

except KeyboardInterrupt:
    print("Exiting Program...")
    mqtt_client.loop_stop()
    board.exit()