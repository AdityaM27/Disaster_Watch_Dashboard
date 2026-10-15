"""
EXP-11: Serial Communication (UART)
Hardware Telemetry Ingestion Bridge for DisasterWatch.

Demonstrates:
- Connecting to an Arduino or virtual serial port via PySerial.
- Parsing incoming CSV sensor streams (e.g., 'Temperature, Humidity, Rain').
- Validating sensor bounds and piping telemetry into the risk evaluation engine.
- Fallback mock mode when physical microcontrollers are not connected.
"""

import sys
import os
import time
import logging

# Ensure backend modules can be imported
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "backend"))

try:
    from services.risk_engine import evaluate_flood_risk, evaluate_heatwave_risk
except ImportError:
    evaluate_flood_risk = None
    evaluate_heatwave_risk = None

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("SerialSensorBridge")


def parse_sensor_csv_line(line: str):
    """
    Parses a CSV line from Arduino in format:
    Temperature(C), Humidity(%), HourlyRain(mm)
    e.g. "34.5, 68.2, 12.0"
    """
    clean_line = line.strip()
    if not clean_line or clean_line.startswith("#"):
        return None

    parts = [p.strip() for p in clean_line.split(",")]
    if len(parts) < 2:
        logger.warning(f"Malformed serial packet: '{clean_line}'")
        return None

    try:
        temp = float(parts[0])
        humidity = float(parts[1])
        rain = float(parts[2]) if len(parts) > 2 else 0.0

        # Physical sanity validation
        if not (-40.0 <= temp <= 65.0 and 0.0 <= humidity <= 100.0):
            logger.warning(f"Sensor reading out of physical bounds: {temp}C, {humidity}%")
            return None

        return {
            "temperature_c": temp,
            "humidity_pct": humidity,
            "hourly_rain_mm": rain,
            "timestamp": time.time()
        }
    except ValueError as e:
        logger.error(f"Failed to parse serial numbers: {e}")
        return None


def run_serial_listener(port: str = "/dev/ttyUSB0", baudrate: int = 9600, mock_mode: bool = True):
    """
    Listens to physical serial port (or runs simulated UART stream if hardware is absent).
    """
    logger.info("==============================================================")
    logger.info(" EXP-11: UART Serial Sensor Ingestion Bridge (DisasterWatch) ")
    logger.info(f" Target Port: {port} | Baud: {baudrate} | Mock Mode: {mock_mode}")
    logger.info("==============================================================")

    if not mock_mode:
        try:
            import serial
            ser = serial.Serial(port, baudrate, timeout=1.0)
            logger.info(f"Connected to physical Arduino on {port}")
            while True:
                raw_bytes = ser.readline()
                if raw_bytes:
                    line = raw_bytes.decode("utf-8", errors="ignore")
                    telemetry = parse_sensor_csv_line(line)
                    if telemetry and evaluate_flood_risk:
                        sev, score, rule, _ = evaluate_flood_risk(telemetry["hourly_rain_mm"], 0.0)
                        logger.info(f"[UART TELEMETRY] Temp: {telemetry['temperature_c']}C, Rain: {telemetry['hourly_rain_mm']}mm -> Risk: {sev} ({score}/10)")
        except ImportError:
            logger.error("pyserial library not installed. Run 'pip install pyserial'")
        except Exception as e:
            logger.warning(f"Serial port unavailable ({e}). Falling back to simulated UART stream...")
            mock_mode = True

    if mock_mode:
        logger.info("[MOCK UART] Simulating live incoming Arduino sensor packets...")
        mock_packets = [
            "31.2, 55.4, 0.0",
            "34.8, 62.1, 2.5",
            "38.5, 70.0, 18.0",
            "43.0, 80.2, 35.5",  # Severe storm / flood threshold
        ]
        for packet in mock_packets:
            time.sleep(1.0)
            telemetry = parse_sensor_csv_line(packet)
            if telemetry:
                f_sev, f_score, f_rule, _ = evaluate_flood_risk(telemetry["hourly_rain_mm"], 0.0)
                h_sev, h_score, h_rule, _ = evaluate_heatwave_risk(telemetry["temperature_c"])
                logger.info(f"[RX SERIAL] Raw: '{packet}' -> Flood Risk: {f_sev} (Score: {f_score}), Heatwave: {h_sev}")
        logger.info("[MOCK UART] Simulation batch complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="EXP-11 UART Serial Reader")
    parser.add_argument("--port", default="/dev/ttyUSB0", help="Serial port path")
    parser.add_argument("--baud", type=int, default=9600, help="Baud rate")
    parser.add_argument("--live", action="store_true", help="Connect to live hardware instead of mock stream")
    args = parser.parse_args()

    run_serial_listener(port=args.port, baudrate=args.baud, mock_mode=not args.live)
