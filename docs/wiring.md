# Wiring Guide

## 1. RC522 RFID → Raspberry Pi 5 (SPI)

| RC522 Pin | Raspberry Pi 5 | Physical Pin | Description |
|----------|----------------|--------------|-------------|
| SDA (SS) | GPIO8          | Pin 24       | SPI CE0     |
| SCK      | GPIO11         | Pin 23       | SPI Clock   |
| MOSI     | GPIO10         | Pin 19       | SPI MOSI    |
| MISO     | GPIO9          | Pin 21       | SPI MISO    |
| RST      | GPIO25         | Pin 22       | Reset       |
| GND      | GND            | Pin 6        | Ground      |
| 3.3V     | 3.3V           | Pin 1        | Power       |

> Note: RC522 因目前 library 限制，使用 legacy `RPi.GPIO` 底層驅動。

---

## 2. Relay Module (SONGLE SRD-05VDC-SL-C)

| Relay Pin | Raspberry Pi 5 | Physical Pin | Description |
|----------|----------------|--------------|-------------|
| IN (S)   | GPIO17         | Pin 11       | Control     |
| VCC      | 5V             | Pin 2 / 4    | Relay Power |
| GND      | GND            | Pin 6        | Common GND  |

Relay 由 **lgpio (RP1-native)** 控制。

---

## 3. LED Indicator (via Relay NO)

RPi 3.3V (Pin 1)
  → LED (+)
  → 1kΩ Resistor
  → Relay NO
  → GND (Pin 6)
