import serial
import csv
import numpy as np
import time

PORT = "COM8"
BAUD = 921600
TARGET_LEN = 128
FILENAME = "csi_data_log0121.csv"

try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    ser.setDTR(False)
    ser.setRTS(False)
    time.sleep(1)
    ser.reset_input_buffer()
    print(f"Connected to {PORT} at {BAUD} baud.")
except Exception as e:
    print(f"Could not open port: {e}")
    exit()

with open(FILENAME, "w", newline="") as file:
    writer = csv.writer(file)
    
    header = ["pc_time", "esp_timestamp", "mac_address", "rssi", "csi_len"]
    for i in range(TARGET_LEN):
        header.append(f"subcarrier_{i}")
    writer.writerow(header)

    print(f"Logging data to {FILENAME}. Press Ctrl+C to stop.")

    while True:
        try:
            line = ser.readline().decode(errors="ignore").strip()

            if not line.startswith("CSI"):
                continue

            parts = [p for p in line.split(",") if p.strip()]

            if len(parts) < 6:
                continue

            esp_ts = parts[1]
            mac_addr = parts[2]
            rssi = int(parts[3])
            csi_len = int(parts[4])
            
            raw_data = np.array(list(map(int, parts[5:])))

            iq_pairs = raw_data.reshape(-1, 2)
            
            amplitudes = np.sqrt(np.sum(np.square(iq_pairs), axis=1))

            if len(amplitudes) > TARGET_LEN:
                amplitudes = amplitudes[:TARGET_LEN]
            else:
                amplitudes = np.pad(amplitudes, (0, TARGET_LEN - len(amplitudes)))

            row = [time.time(), esp_ts, mac_addr, rssi, csi_len] + amplitudes.tolist()
            
            writer.writerow(row)
            file.flush()

            print(f"Saved Row | ESP_TS: {esp_ts} | RSSI: {rssi} | Subcarriers: {len(amplitudes)}")

        except KeyboardInterrupt:
            print("\nStopping data collection...")
            break
        except Exception as e:
            print(f"Error processing line: {e}")

ser.close()
