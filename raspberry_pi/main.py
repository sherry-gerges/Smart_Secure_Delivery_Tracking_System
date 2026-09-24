import board
import busio
from digitalio import DigitalInOut
from adafruit_pn532.i2c import PN532_I2C
from gpiozero import DigitalInputDevice
from gpiozero import Servo
from gpiozero import LED
import paho.mqtt.client as mqtt
import ssl
from time import sleep, time

# ============================================================
#                    GPIO CONFIGURATION
# ============================================================

IR_PIN = 17
SERVO_PIN = 18
LED_PIN = 23

# ============================================================
#                    MQTT CONFIGURATION
# ============================================================

MQTT_HOST = "host"
MQTT_PORT = 8883

MQTT_USERNAME = "username"
MQTT_PASSWORD = "password"

# ============================================================
#                    MQTT TOPICS
# ============================================================

NFC_TOPIC = "delivery/package/nfc"
EVENT_TOPIC = "delivery/events"
PRESENCE_TOPIC = "delivery/package/presence"
SERVO_TOPIC = "delivery/servo"
STATUS_TOPIC = "delivery/status"


# ============================================================
#                    NFC UID CONFIGURATION
# ============================================================

PACKAGE_UID = "7378BD02"
DRIVER_UID = "B359B834"


# ============================================================
#                    TIMING
# ============================================================

# Time the driver has access to the compartment
DRIVER_OPEN_TIME = 5

# Time allowed for IR to detect the package
PACKAGE_DETECTION_TIMEOUT = 5

# Time the driver has access at destination
DELIVERY_OPEN_TIME = 5


# ============================================================
#                    SYSTEM STATES
# ============================================================

WAITING_FOR_DRIVER = "WAITING_FOR_DRIVER"
WAITING_FOR_PACKAGE = "WAITING_FOR_PACKAGE"
IN_TRANSIT = "IN_TRANSIT"
ARRIVED = "ARRIVED"
DELIVERED = "DELIVERED"
SECURITY_ALERT = "SECURITY_ALERT"

# ============================================================
#                    INITIAL STATE
# ============================================================

current_state = WAITING_FOR_DRIVER


# ============================================================
#                    PN532 SETUP
# ============================================================

i2c = busio.I2C(
    board.SCL,
    board.SDA
)

reset_pin = DigitalInOut(board.D6)
req_pin = DigitalInOut(board.D5)

pn532 = PN532_I2C(
    i2c,
    debug=False,
    reset=reset_pin,
    req=req_pin
)


# ============================================================
#                    CHECK PN532
# ============================================================

ic, ver, rev, support = pn532.firmware_version

print("--------------------------------")
print("PN532 detected!")
print("Firmware:", ver, ".", rev)
print("--------------------------------")

pn532.SAM_configuration()


# ============================================================
#                     SETUP
# ============================================================

ir_sensor = DigitalInputDevice(IR_PIN)
servo = Servo(SERVO_PIN)
led = LED(LED_PIN)


# ============================================================
#                    SERVO FUNCTIONS
# ============================================================

def unlock_servo():

    print("SERVO → OPEN")

    servo.value = 1

    led.on()


def lock_servo():

    print("SERVO → CLOSE")

    servo.value = -1

    led.off()


# ============================================================
#                    MQTT PUBLISH FUNCTIONS
# ============================================================

def publish_event(event):

    result = client.publish(
        EVENT_TOPIC,
        event
    )

    if result.rc == mqtt.MQTT_ERR_SUCCESS:

        print("Event sent:", event)

    else:

        print("Failed to send event:", event)


def publish_status(status):

    result = client.publish(
        STATUS_TOPIC,
        status
    )

    if result.rc == mqtt.MQTT_ERR_SUCCESS:

        print("Status sent:", status)


def publish_presence(value):

    result = client.publish(
        PRESENCE_TOPIC,
        value
    )

    if result.rc == mqtt.MQTT_ERR_SUCCESS:

        print("Presence sent:", value)


# ============================================================
#                    MQTT CALLBACK
# ============================================================

def on_connect(client, userdata, flags, rc):

    if rc == 0:

        print("Connected to HiveMQ!")

        client.subscribe(SERVO_TOPIC)

        print("Subscribed to:", SERVO_TOPIC)

    else:

        print("MQTT connection failed.")

        print("Return code:", rc)


# ============================================================
#                    MQTT MESSAGE CALLBACK
# ============================================================

def on_message(client, userdata, msg):

    message = msg.payload.decode().strip()

    print("\nMQTT command received:")

    print("Topic:", msg.topic)

    print("Message:", message)


    # ========================================================
    # SERVO COMMANDS FROM NODE-RED
    # ========================================================

    if msg.topic == SERVO_TOPIC:

        if message == "UNLOCK":

            unlock_servo()

        elif message == "LOCK":

            lock_servo()


# ============================================================
#                    MQTT CLIENT
# ============================================================

client = mqtt.Client()

client.username_pw_set(
    MQTT_USERNAME,
    MQTT_PASSWORD
)

client.tls_set(
    cert_reqs=ssl.CERT_REQUIRED
)

client.on_connect = on_connect

client.on_message = on_message


# ============================================================
#                    CONNECT TO HIVEMQ
# ============================================================

print("Connecting to HiveMQ...")

client.connect(
    MQTT_HOST,
    MQTT_PORT,
    60
)

client.loop_start()


# ============================================================
#                    START SYSTEM
# ============================================================

lock_servo()

print("--------------------------------")
print("Smart Secure Delivery System")
print("--------------------------------")

print("Current state:", current_state)

publish_status(current_state)


# ============================================================
#                    VARIABLES
# ============================================================

last_uid = None

last_ir_state = None

package_wait_start = None


# ============================================================
#                    MAIN LOOP
# ============================================================

try:

    while True:


        # ====================================================
        # 1. NFC SCANNING
        # ====================================================

        uid = pn532.read_passive_target(
            timeout=0.5
        )


        if uid is not None:

            uid_string = "".join(
                "{:02X}".format(x)
                for x in uid
            )


            # Prevent repeated scanning
            if uid_string != last_uid:

                print("\n==============================")

                print("NFC CARD DETECTED")

                print("UID:", uid_string)

                print("Current state:", current_state)


                # =================================================
                # STATE 1
                # WAITING FOR DRIVER
                # =================================================

                if current_state == WAITING_FOR_DRIVER:


                    # ---------------------------------------------
                    # CORRECT DRIVER
                    # ---------------------------------------------

                    if uid_string == DRIVER_UID:

                        print("AUTHORIZED DRIVER")

                        publish_event(
                            "AUTHORIZED_DRIVER"
                        )


                        # Driver receives access
                        unlock_servo()

                        print(
                            "Driver access granted."
                        )

                        print(
                            "Waiting",
                            DRIVER_OPEN_TIME,
                            "seconds..."
                        )

                        sleep(DRIVER_OPEN_TIME)


                        # Lock again
                        lock_servo()


                        # Now package loading stage
                        current_state = WAITING_FOR_PACKAGE

                        print(
                            "Driver access finished."
                        )

                        print(
                            "Current state:",
                            current_state
                        )

                        publish_status(
                            current_state
                        )


                    # ---------------------------------------------
                    # WRONG CARD
                    # ---------------------------------------------

                    else:

                        print(
                            "UNAUTHORIZED DRIVER"
                        )

                        publish_event(
                            "UNAUTHORIZED_ACCESS"
                        )

                        current_state = SECURITY_ALERT

                        publish_status(
                            current_state
                        )

                        # Keep servo locked
                        lock_servo()


                # =================================================
                # STATE 2
                # WAITING FOR PACKAGE
                # =================================================

                elif current_state == WAITING_FOR_PACKAGE:


                    # ---------------------------------------------
                    # PACKAGE CARD
                    # ---------------------------------------------

                    if uid_string == PACKAGE_UID:

                        print(
                            "PACKAGE CARD DETECTED"
                        )

                        print(
                            "PACKAGE_102"
                        )


                        # Send package UID
                        client.publish(
                            NFC_TOPIC,
                            uid_string
                        )


                        # Open compartment
                        unlock_servo()


                        print(
                            "Put package in the compartment."
                        )

                        print(
                            "Waiting for IR detection..."
                        )


                        # Start timeout
                        package_wait_start = time()


                    # ---------------------------------------------
                    # WRONG CARD
                    # ---------------------------------------------

                    else:

                        print(
                            "Unauthorized card "
                            "during package loading."
                        )

                        publish_event(
                            "UNAUTHORIZED_ACCESS"
                        )

                        current_state = SECURITY_ALERT

                        publish_status(
                            current_state
                        )

                        lock_servo()


                # =================================================
                # STATE 3
                # IN TRANSIT
                # =================================================

                elif current_state == IN_TRANSIT:


                    # Driver arrives at destination
                    if uid_string == DRIVER_UID:

                        print(
                            "AUTHORIZED DRIVER "
                            "AT DESTINATION"
                        )


                        # Tell Node-RED
                        publish_event(
                            "DRIVER_ARRIVED"
                        )


                        # Update state
                        current_state = ARRIVED

                        publish_status(
                            current_state
                        )


                        # Open compartment
                        unlock_servo()


                        print(
                            "Driver can take the package."
                        )

                        print(
                            "Waiting",
                            DELIVERY_OPEN_TIME,
                            "seconds..."
                        )

                        sleep(
                            DELIVERY_OPEN_TIME
                        )


                        # Close compartment
                        lock_servo()


                        # Delivery completed
                        current_state = DELIVERED

                        publish_event(
                            "DELIVERED"
                        )

                        publish_status(
                            current_state
                        )


                        print(
                            "DELIVERY COMPLETED"
                        )


                    # Wrong card at destination
                    else:

                        print(
                            "UNAUTHORIZED ACCESS "
                            "AT DESTINATION"
                        )

                        publish_event(
                            "UNAUTHORIZED_ACCESS"
                        )

                        current_state = SECURITY_ALERT

                        publish_status(
                            current_state
                        )

                        lock_servo()


                # =================================================
                # OTHER STATES
                # =================================================

                elif current_state == SECURITY_ALERT:

                    print(
                        "System is in SECURITY_ALERT."
                    )

                    print(
                        "No access will be granted."
                    )

                    lock_servo()


                elif current_state == DELIVERED:

                    print( "Delivery already completed.")


                print("==============================")


                # Save UID
                last_uid = uid_string


        else:

            # Allow same card to be scanned again
            # after it is removed

            last_uid = None


        # ====================================================
        # 2. IR SENSOR
        # ====================================================

        current_ir_state = ir_sensor.value


        # Detect state changes only
        if current_ir_state != last_ir_state:


            # =================================================
            # PACKAGE PRESENT
            # =================================================

            if current_ir_state == 1:

                print(
                    "\nPACKAGE PRESENT"
                )


                publish_presence(
                    "true"
                )


                # ---------------------------------------------
                # Package successfully loaded
                # ---------------------------------------------

                if current_state == WAITING_FOR_PACKAGE:

                    print(
                        "Package detected by IR."
                    )


                    # Close compartment
                    lock_servo()


                    # Start transportation
                    current_state = IN_TRANSIT


                    publish_event(
                        "PACKAGE_LOADED"
                    )


                    publish_event(
                        "DELIVERY_STARTED"
                    )


                    publish_status(
                        current_state
                    )


                    print(
                        "DELIVERY STARTED"
                    )


            # =================================================
            # PACKAGE MISSING
            # =================================================

            else:

                print(
                    "\nPACKAGE MISSING"
                )


                publish_presence(
                    "false"
                )


                # ---------------------------------------------
                # IMPORTANT:
                # Do NOT report missing package during normal
                # operation.
                #
                # Only report it while we are waiting for IR
                # after opening the package compartment.
                # ---------------------------------------------

                if current_state == WAITING_FOR_PACKAGE:

                    print(
                        "Package has not been detected."
                    )


            # Save IR state
            last_ir_state = current_ir_state


        # ====================================================
        # 3. PACKAGE DETECTION TIMEOUT
        # ====================================================

        if (
            current_state == WAITING_FOR_PACKAGE
            and package_wait_start is not None
        ):

            elapsed = time() - package_wait_start


            if elapsed >= PACKAGE_DETECTION_TIMEOUT:

                # Check one last time
                if ir_sensor.value != 1:

                    print(
                        "\nPACKAGE MISSING!"
                    )


                    # Close servo
                    lock_servo()


                    # Tell Node-RED
                    publish_event(
                        "MISSING_PACKAGE"
                    )


                    current_state = SECURITY_ALERT


                    publish_status(
                        current_state
                    )


                    # Reset timer
                    package_wait_start = None


                else:

                    # Package was detected
                    package_wait_start = None


        # ====================================================
        # SMALL LOOP DELAY
        # ====================================================

        sleep(0.2)


# ============================================================
#                    STOP PROGRAM
# ============================================================

except KeyboardInterrupt:

    print("\nSystem stopped.")


    # Stop MQTT
    client.loop_stop()


    # Disconnect MQTT
    client.disconnect()


    # Close devices
    ir_sensor.close()

    led.close()


    # Lock servo
    servo.value = -1


    print(
        "Servo locked."
    )
