"""
Intelligent Ventilation Control System for Underground Road Tunnels
====================================================================
Bachelor's Thesis - Andrei Blebea
National University of Science and Technology Politehnica Bucharest
Faculty of Transportation, 2025

Description:
    Demonstration script for automatic fan control based on air quality
    sensor data (PM2.5, NO2, CO). Implements a 4-level alert algorithm
    with a hysteresis loop to prevent rapid state switching.

Hardware used in prototype:
    - Raspberry Pi 5
    - MQ-135 gas sensor (general air quality)
    - 2x Fan MF50200V1-1000U-A99 (5V DC)
    - IRLZ44N MOSFET transistors + 1kOhm resistors
    - 1N4007 rectifier diodes

Usage:
    On real Raspberry Pi:   python3 ventilatie_tunel.py
    In simulation mode:     python3 ventilatie_tunel.py --simulate
"""

import time
import argparse
import random

# ─────────────────────────────────────────────
#  GPIO Pin Configuration (BCM numbering)
# ─────────────────────────────────────────────
FAN1_PIN   = 18   # Fan 1
FAN2_PIN   = 23   # Fan 2
SENSOR_PIN = 17   # MQ-135 digital output

# ─────────────────────────────────────────────
#  Alert Thresholds (based on Table 4, Thesis)
#  Units: PM2.5 in µg/m³, CO in ppm, NO2 in µg/m³
# ─────────────────────────────────────────────
THRESHOLDS = {
    "MODERATE": {"PM25": 15,  "CO": 10,  "NO2":  50},
    "HIGH":     {"PM25": 35,  "CO": 30,  "NO2": 100},
    "CRITICAL": {"PM25": 75,  "CO": 50,  "NO2": 200},
}

# Hysteresis: system drops to a lower level only when values fall
# below the threshold multiplied by this factor
HYSTERESIS_FACTOR = 0.85

# Fan speed per alert level (0.0 – 1.0)
FAN_SPEED = {
    "STANDBY":  0.10,
    "MODERATE": 0.40,
    "HIGH":     0.75,
    "CRITICAL": 1.00,
}

# Sensor polling interval (seconds)
READ_INTERVAL = 10


# ─────────────────────────────────────────────
#  Hardware detection: Raspberry Pi or PC
# ─────────────────────────────────────────────
def detect_hardware():
    """Returns True if running on a Raspberry Pi with GPIO available."""
    try:
        import RPi.GPIO as GPIO
        return True
    except (ImportError, RuntimeError):
        return False


# ─────────────────────────────────────────────
#  GPIO Controller (real hardware)
# ─────────────────────────────────────────────
class GPIOController:
    def __init__(self):
        import RPi.GPIO as GPIO
        self.GPIO = GPIO
        GPIO.setmode(GPIO.BCM)
        GPIO.setwarnings(False)
        GPIO.setup(FAN1_PIN, GPIO.OUT)
        GPIO.setup(FAN2_PIN, GPIO.OUT)
        GPIO.setup(SENSOR_PIN, GPIO.IN)

        # PWM at 1 kHz for smooth speed control
        self.pwm1 = GPIO.PWM(FAN1_PIN, 1000)
        self.pwm2 = GPIO.PWM(FAN2_PIN, 1000)
        self.pwm1.start(0)
        self.pwm2.start(0)

    def set_fan_speed(self, speed_fraction):
        """Sets fan speed via PWM duty cycle (0.0 – 1.0)."""
        duty = speed_fraction * 100
        self.pwm1.ChangeDutyCycle(duty)
        self.pwm2.ChangeDutyCycle(duty)

    def read_sensor_digital(self):
        """Reads digital output from MQ-135 (LOW = polluted air)."""
        return self.GPIO.input(SENSOR_PIN)

    def cleanup(self):
        self.pwm1.stop()
        self.pwm2.stop()
        self.GPIO.cleanup()


# ─────────────────────────────────────────────
#  Simulated Controller (demo on PC)
# ─────────────────────────────────────────────
class SimulatedController:
    def __init__(self):
        self._current_speed = 0.0
        print("  [SIMULATION] GPIO unavailable — running in demo mode.")

    def set_fan_speed(self, speed_fraction):
        self._current_speed = speed_fraction

    def read_sensor_digital(self):
        # Not used in simulated mode with analog data
        return 1

    def cleanup(self):
        pass


# ─────────────────────────────────────────────
#  Simulated sensor data generator
# ─────────────────────────────────────────────
def generate_simulated_readings(step):
    """
    Simulates a realistic urban traffic scenario across 4 phases:
      Phase 0 — Low traffic  (Standby)
      Phase 1 — Moderate traffic
      Phase 2 — Heavy traffic / Critical levels
      Phase 3 — Recovery after active ventilation
    Each phase lasts approximately 8 polling cycles.
    """
    phase = (step // 8) % 4

    if phase == 0:   # Low traffic
        pm25 = random.uniform(5,  14)
        co   = random.uniform(3,   9)
        no2  = random.uniform(15, 45)
    elif phase == 1: # Moderate traffic
        pm25 = random.uniform(16, 34)
        co   = random.uniform(11, 29)
        no2  = random.uniform(55, 95)
    elif phase == 2: # Heavy traffic / critical
        pm25 = random.uniform(40, 90)
        co   = random.uniform(35, 65)
        no2  = random.uniform(110, 230)
    else:            # Recovery after ventilation
        pm25 = random.uniform(10, 30)
        co   = random.uniform(8,  25)
        no2  = random.uniform(30, 85)

    return round(pm25, 1), round(co, 1), round(no2, 1)


# ─────────────────────────────────────────────
#  Alert level determination
# ─────────────────────────────────────────────
def get_alert_level(pm25, co, no2, current_level):
    """
    Determines the alert level based on sensor readings and the
    current level (used to apply hysteresis on the way down).

    Evaluation is hierarchical: CRITICAL is checked first,
    then HIGH, then MODERATE. If none are triggered, the system
    falls back to STANDBY — but only after hysteresis clears.

    Returns: "STANDBY" | "MODERATE" | "HIGH" | "CRITICAL"
    """
    # Check most critical level first
    if (pm25 > THRESHOLDS["CRITICAL"]["PM25"] or
            co  > THRESHOLDS["CRITICAL"]["CO"]   or
            no2 > THRESHOLDS["CRITICAL"]["NO2"]):
        return "CRITICAL"

    if (pm25 > THRESHOLDS["HIGH"]["PM25"] or
            co  > THRESHOLDS["HIGH"]["CO"]   or
            no2 > THRESHOLDS["HIGH"]["NO2"]):
        return "HIGH"

    if (pm25 > THRESHOLDS["MODERATE"]["PM25"] or
            co  > THRESHOLDS["MODERATE"]["CO"]   or
            no2 > THRESHOLDS["MODERATE"]["NO2"]):
        return "MODERATE"

    # Hysteresis: only drop to STANDBY if values are well below
    # the lowest threshold (prevents rapid oscillation / "flapping")
    if current_level != "STANDBY":
        hyst_pm25 = THRESHOLDS["MODERATE"]["PM25"] * HYSTERESIS_FACTOR
        hyst_co   = THRESHOLDS["MODERATE"]["CO"]   * HYSTERESIS_FACTOR
        hyst_no2  = THRESHOLDS["MODERATE"]["NO2"]  * HYSTERESIS_FACTOR
        if pm25 > hyst_pm25 or co > hyst_co or no2 > hyst_no2:
            return current_level  # hold current level

    return "STANDBY"


# ─────────────────────────────────────────────
#  Terminal status display
# ─────────────────────────────────────────────
LEVEL_LABELS = {
    "STANDBY":  "[ STANDBY  ]",
    "MODERATE": "[ MODERATE ]",
    "HIGH":     "[   HIGH   ]",
    "CRITICAL": "[ CRITICAL!]",
}

def print_status(step, pm25, co, no2, level, speed):
    separator = "-" * 62
    print(separator)
    print(f"  Cycle #{step:>3}  |  {time.strftime('%H:%M:%S')}")
    print(f"  PM2.5 : {pm25:>6.1f} µg/m³   (moderate threshold: {THRESHOLDS['MODERATE']['PM25']} µg/m³)")
    print(f"  CO    : {co:>6.1f} ppm      (moderate threshold: {THRESHOLDS['MODERATE']['CO']} ppm)")
    print(f"  NO2   : {no2:>6.1f} µg/m³   (moderate threshold: {THRESHOLDS['MODERATE']['NO2']} µg/m³)")
    print(f"  Level : {LEVEL_LABELS[level]}   Fan speed: {int(speed * 100):>3}%")
    print(separator)


# ─────────────────────────────────────────────
#  Main control loop
# ─────────────────────────────────────────────
def run(simulate=False):
    use_hardware = detect_hardware() and not simulate

    if use_hardware:
        print("\n  Raspberry Pi hardware detected. Starting real system...\n")
        controller = GPIOController()
    else:
        print("\n  Starting system in SIMULATION MODE (demo)...\n")
        controller = SimulatedController()

    print("=" * 62)
    print("   VENTILATION CONTROL SYSTEM — UNDERGROUND ROAD TUNNEL")
    print("   Politehnica Bucharest | Bachelor's Thesis 2025")
    print("=" * 62)
    print(f"  Poll interval   : {READ_INTERVAL}s")
    print(f"  Hysteresis      : {int(HYSTERESIS_FACTOR * 100)}%")
    print(f"  Active thresholds: PM2.5 / CO / NO2 (WHO standards)")
    print("=" * 62)
    print("  Press Ctrl+C to stop the system.\n")

    current_level = "STANDBY"
    step = 0

    try:
        while True:
            step += 1

            # Step 1: Read sensors
            if use_hardware:
                # On real hardware the MQ-135 provides a digital signal.
                # In a full deployment, analog/I2C sensors would provide
                # precise numeric values for PM2.5, CO and NO2.
                raw = controller.read_sensor_digital()
                pm25 = 5.0  if raw else 45.0
                co   = 5.0  if raw else 40.0
                no2  = 20.0 if raw else 130.0
            else:
                pm25, co, no2 = generate_simulated_readings(step)

            # Step 2: Determine alert level (with hysteresis)
            new_level = get_alert_level(pm25, co, no2, current_level)

            # Step 3: Update fan speed if level has changed
            if new_level != current_level:
                current_level = new_level
                controller.set_fan_speed(FAN_SPEED[current_level])

            # Step 4: Print current status to terminal
            print_status(step, pm25, co, no2, current_level, FAN_SPEED[current_level])

            # Step 5: Wait until next polling cycle
            time.sleep(READ_INTERVAL)

    except KeyboardInterrupt:
        print("\n\n  System stopped manually (Ctrl+C).")
    finally:
        controller.set_fan_speed(0.0)
        controller.cleanup()
        print("  GPIO released. Goodbye.\n")


# ─────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Tunnel ventilation control system — Bachelor's Thesis, Andrei Blebea"
    )
    parser.add_argument(
        "--simulate",
        action="store_true",
        help="Run in simulation mode (no real GPIO required, useful on PC)"
    )
    args = parser.parse_args()
    run(simulate=args.simulate)
