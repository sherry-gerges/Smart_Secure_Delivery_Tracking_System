# 📦 Smart Secure Delivery Tracking System

An IoT-based smart delivery system designed to secure package loading, transportation, and delivery using **Raspberry Pi, NFC, IR sensing, MQTT, Node-RED, GPS tracking, Telegram, Gmail, and a web dashboard**.

The system verifies authorized access, detects whether the package has been loaded, tracks the shipment location, detects arrival at the destination, and provides real-time notifications and security alerts.

---

## 1. 📋 Project Overview

The system automates the delivery process through a Raspberry Pi connected to:

* PN532 NFC reader for identity and package identification
* IR sensor for package presence detection
* Servo motor for compartment locking/unlocking
* LED for access indication
* HiveMQ Cloud using MQTT for communication
* Node-RED for processing, notifications, and dashboard visualization
* OwnTracks for GPS location tracking
* Worldmap for real-time shipment visualization
* Telegram for delivery notifications
* Gmail for security alerts

### Main workflow

```text
Driver NFC
    ↓
Authorized?
    ↓
Package NFC
    ↓
Package detected by IR?
    ↓
Delivery starts
    ↓
GPS tracking
    ↓
Driver scans at destination
    ↓
Package delivered
```

---

## 2. 🔧 System Components

| Component    | Purpose                         |
| ------------ | ------------------------------- |
| Raspberry Pi | Main controller                 |
| PN532 NFC    | Reads driver/package NFC cards  |
| IR Sensor    | Detects package presence        |
| Servo Motor  | Locks/unlocks the compartment   |
| LED          | Indicates compartment access    |
| HiveMQ Cloud | MQTT communication              |
| Node-RED     | Data processing and dashboard   |
| OwnTracks    | GPS location source             |
| Worldmap     | Shipment location visualization |
| Telegram     | Delivery notifications          |
| Gmail        | Security alerts                 |

---

## 3. 🔌 Hardware Connections

### Raspberry Pi

| Component   | Raspberry Pi Pin |
| ----------- | ---------------: |
| PN532 SDA   |     SDA / GPIO 2 |
| PN532 SCL   |     SCL / GPIO 3 |
| PN532 RESET |           GPIO 6 |
| PN532 REQ   |           GPIO 5 |
| IR Sensor   |          GPIO 17 |
| Servo       |          GPIO 18 |
| LED         |          GPIO 23 |

### PN532

The PN532 is connected to the Raspberry Pi using **I2C**.

The Python program initializes it using:

```python
i2c = busio.I2C(
    board.SCL,
    board.SDA
)
```

and uses:

```python
reset_pin = DigitalInOut(board.D6)
req_pin = DigitalInOut(board.D5)
```

---

## 4. 📳 NFC Cards

Two NFC cards are used by the system.

| Card         | UID        | Purpose                |
| ------------ | ---------- | ---------------------- |
| Driver Card  | `B359B834` | Driver authentication  |
| Package Card | `7378BD02` | Package identification |

The customer does not use an NFC card in the current implementation.

---

## 5. 🐍 Raspberry Pi Software

The main program is:

```text
raspberry_pi/delivery_system.py
```

### Python libraries

| Library                        | Purpose                                        |
| ------------------------------ | ---------------------------------------------- |
| `adafruit-blinka`              | Hardware interface for CircuitPython libraries |
| `adafruit-circuitpython-pn532` | PN532 NFC communication                        |
| `gpiozero`                     | GPIO, LED, IR and servo control                |
| `paho-mqtt`                    | MQTT communication                             |
| `ssl`                          | TLS connection to HiveMQ                       |
| `time`                         | Timing and delays                              |

Install the required packages with:

```bash
pip install -r requirements.txt
```

---

## 6. 📡 MQTT Communication

The system uses **HiveMQ Cloud** over secure MQTT/TLS.

### MQTT configuration

| Setting       | Value               |
| ------------- | ------------------- |
| Protocol      | MQTT                |
| Security      | TLS                 |
| Port          | `8883`              |
| Broker        | HiveMQ Cloud        |
| Communication | Publish / Subscribe |

Credentials are intentionally not included in this repository.

---

## 7. 🔗 MQTT Topics

| Topic                       | Direction               | Purpose                 |
| --------------------------- | ----------------------- | ----------------------- |
| `delivery/package/nfc`      | Raspberry Pi → Node-RED | NFC package UID         |
| `delivery/events`           | Raspberry Pi → Node-RED | System events           |
| `delivery/package/presence` | Raspberry Pi → Node-RED | IR package status       |
| `delivery/servo`            | Node-RED → Raspberry Pi | Servo commands          |
| `delivery/status`           | Raspberry Pi / Node-RED | Current delivery status |

---

## 8. 🔄 Delivery States

The Raspberry Pi uses the following states:

```text
WAITING_FOR_DRIVER
        ↓
WAITING_FOR_PACKAGE
        ↓
IN_TRANSIT
        ↓
ARRIVED
        ↓
DELIVERED
```

A security problem moves the system to:

```text
SECURITY_ALERT
```

---

## 9. 🚚 Delivery Process

### Step 1 — Driver Authentication

The system starts in:

```text
WAITING_FOR_DRIVER
```

The driver scans the NFC card.

If the UID matches:

```text
B359B834
```

the system publishes:

```text
AUTHORIZED_DRIVER
```

The servo unlocks for 5 seconds and then locks again.

The system moves to:

```text
WAITING_FOR_PACKAGE
```

---

### Step 2 — Package Identification

The package NFC card is scanned.

Expected UID:

```text
7378BD02
```

The system publishes the UID to:

```text
delivery/package/nfc
```

The servo unlocks and the package can be placed inside the compartment.

---

### Step 3 — Package Detection

The IR sensor checks whether the package is present.

If detected:

```text
PACKAGE_LOADED
```

and:

```text
DELIVERY_STARTED
```

are published.

The compartment is locked and the system enters:

```text
IN_TRANSIT
```

If the package is not detected within the configured timeout:

```text
MISSING_PACKAGE
```

is published and the system enters:

```text
SECURITY_ALERT
```

---

### Step 4 — Shipment Tracking

OwnTracks provides the current GPS coordinates.

Node-RED receives the location through:

```text
owntracks/sherrymegally/a15
```

The location function:

* Calculates the distance to the destination
* Detects arrival
* Stores the actual movement route
* Displays the current shipment position
* Keeps the route visible after arrival
* Displays fixed start and destination points

The route represents the **actual locations received during shipment movement**.

It does not draw a predefined straight line between the start and destination.

---

### Step 5 — Destination Authentication

When the driver reaches the destination, the driver scans the authorized NFC card again.

The system publishes:

```text
DRIVER_ARRIVED
```

The servo unlocks for 5 seconds.

The driver can take the package.

After the compartment is locked, the system publishes:

```text
DELIVERED
```

The final state becomes:

```text
DELIVERED
```

---

## 10. 🔐 Security Handling

If an unauthorized NFC card is detected, the system publishes:

```text
UNAUTHORIZED_ACCESS
```

The servo remains locked and the system enters:

```text
SECURITY_ALERT
```

Node-RED sends a security notification through Gmail.

The same mechanism is used if the package is not detected during the package-loading stage.

---

## 11. 🔄 Node-RED Architecture

The Node-RED implementation is divided into two main flows.

### Dashboard / Events Flow

```text
MQTT: delivery/package/nfc
        ↓
Identify Package
        ↓
Dashboard

MQTT: delivery/package/presence
        ↓
Package Presence
        ↓
Dashboard

MQTT: delivery/events
        ↓
Delivery State Manager
        ├── Telegram
        ├── Gmail
        ├── Dashboard
        └── MQTT Status
```

### Location Flow

```text
OwnTracks MQTT
        ↓
Location Function
        ├── Worldmap
        ├── Distance Gauge
        └── Location Status
```

---

## 12. 📊 Node-RED Dashboard

The dashboard displays:

| Information             | Dashboard element |
| ----------------------- | ----------------- |
| Last NFC card           | Text              |
| Package presence        | Text              |
| Package ID              | Template          |
| Current status          | Template          |
| Last event              | Template          |
| Timestamp               | Template          |
| Distance to destination | Gauge             |
| Shipment location       | Worldmap          |
| Shipment route          | Worldmap          |

---

## 13. 🗺️ Worldmap

The Worldmap contains three types of objects:

### Fixed start point

Represents the location where the shipment begins.

### Fixed destination point

Represents the expected delivery destination.

### Moving shipment

The truck marker represents the current GPS position.

### Shipment route

The route is generated from the GPS points received from OwnTracks.

```text
Start ● ── ● ── ● ── 🚚 ── ● Destination
       actual movement points
```

The route is not generated as a predefined line between the two fixed points.

The route remains visible after the shipment reaches the destination.

---

## 14. 🔔 Notifications

### Telegram

Telegram notifications are generated for major delivery events:

* Delivery started
* Driver arrived
* Package delivered

### Gmail

Gmail is used for security-related events:

* Unauthorized access
* Missing package

---

## 15. 📦 Node-RED Packages

The Node-RED project uses:

| Package                         | Purpose                     |
| ------------------------------- | --------------------------- |
| `node-red-dashboard`            | Dashboard UI                |
| `node-red-contrib-web-worldmap` | GPS/world map visualization |
| `node-red-contrib-telegrambot`  | Telegram notifications      |
| `node-red-node-email`           | Gmail notifications         |

---

## 16. 📁 Repository Structure

```text
Smart-Secure-Delivery-Tracking-System/
│
├── raspberry_pi/
│   ├── main.py
│   └── libraries.txt
│
├── node_red/
│   ├── the_whole_flow.json
│   └── location_flow.json
│
├── docs/
│   └── images/
│
├── README.md
└── .gitignore
```

---

## 17. 🔐 Security Notes

Sensitive credentials are intentionally excluded from the repository.

Do not commit:

```text
MQTT passwords
Telegram bot tokens
Gmail passwords
API keys
.env files
```

Credentials should be configured locally on the Raspberry Pi and Node-RED environment.

---

## 18. ✨ Project Features

* NFC-based driver authentication
* NFC-based package identification
* IR package detection
* Servo-controlled compartment
* LED access indication
* Secure MQTT communication
* Delivery state management
* GPS shipment tracking
* Actual movement route visualization
* Fixed start and destination markers
* Distance-to-destination calculation
* Arrival detection
* Telegram notifications
* Gmail security alerts
* Node-RED dashboard
* Security alert state
* End-to-end delivery workflow

---

## 19. 💻 Technologies

```text
Python
Raspberry Pi
PN532 NFC
GPIO
MQTT
HiveMQ Cloud
Node-RED
OwnTracks
Worldmap
Telegram
Gmail
```

---

## 20. 👩‍💻 Author

**Sherry Gerges**

Project follow-up and supervision: **Eng. Menna Khaled**

