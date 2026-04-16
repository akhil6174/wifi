import serial
import csv
import numpy as np
import time

# --- Configuration ---
PORT = "COM8"
BAUD = 921600  # Matches your ESP32 high-speed setting
TARGET_LEN = 128  # Number of subcarrier amplitudes to keep
FILENAME = "csi_data_log0121.csv"

# --- Initialize Serial ---
try:
    ser = serial.Serial(PORT, BAUD, timeout=1)
    # Prevent ESP32 from resetting on connection
    ser.setDTR(False)
    ser.setRTS(False)
    time.sleep(1)
    ser.reset_input_buffer()
    print(f"Connected to {PORT} at {BAUD} baud.")
except Exception as e:
    print(f"Could not open port: {e}")
    exit()

# --- Prepare CSV File ---
with open(FILENAME, "w", newline="") as file:
    writer = csv.writer(file)
    
    # Updated Header for your new format
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

            # Split and remove any trailing empty strings from commas
            parts = [p for p in line.split(",") if p.strip()]

            # Based on your output: CSI, 6622573, A4:F0:0F:5B:78:25, -52, 256, [DATA...]
            if len(parts) < 6:
                continue

            esp_ts = parts[1]
            mac_addr = parts[2]
            rssi = int(parts[3])
            csi_len = int(parts[4])
            
            # The remaining parts are the raw I and Q values
            raw_data = np.array(list(map(int, parts[5:])))

            # 1. Group into [I, Q] pairs
            # Since each subcarrier has 2 values, we reshape to (N, 2)
            iq_pairs = raw_data.reshape(-1, 2)
            
            # 2. Calculate Amplitude: sqrt(I^2 + Q^2)
            amplitudes = np.sqrt(np.sum(np.square(iq_pairs), axis=1))

            # 3. Truncate or Pad to TARGET_LEN
            if len(amplitudes) > TARGET_LEN:
                amplitudes = amplitudes[:TARGET_LEN]
            else:
                amplitudes = np.pad(amplitudes, (0, TARGET_LEN - len(amplitudes)))

            # 4. Construct Row
            row = [time.time(), esp_ts, mac_addr, rssi, csi_len] + amplitudes.tolist()
            
            writer.writerow(row)
            
            # Optional: Periodic flush to disk (every row is safer but slower)
            file.flush()

            print(f"Saved Row | ESP_TS: {esp_ts} | RSSI: {rssi} | Subcarriers: {len(amplitudes)}")

        except KeyboardInterrupt:
            print("\nStopping data collection...")
            break
        except Exception as e:
            print(f"Error processing line: {e}")

ser.close()