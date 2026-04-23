from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
import pandas as pd
import numpy as np
import io

app = Flask(__name__, static_folder='.')
CORS(app)
 
DEFAULT_DATA = {
    "day":         [1,    2,    3,    4,    5,    6,    7,    8,    9,    10],
    "temperature": [22.0, None, 25.0, 27.0, None, 30.0, 31.0, 29.0, None, 26.0],
    "humidity":    [60.0, 63.0, None, 68.0, 70.0, None, 75.0, 72.0, 69.0, 65.0],
}

session_df = pd.DataFrame(DEFAULT_DATA)

def df_to_records(df):
    records = []
    for _, row in df.iterrows():
        records.append({
            "day":         int(row["day"]),
            "temperature": None if pd.isna(row["temperature"]) else round(float(row["temperature"]), 1),
            "humidity":    None if pd.isna(row["humidity"])    else round(float(row["humidity"]), 1),
        })
    return records

def count_nan(df):
    return int(df["temperature"].isna().sum() + df["humidity"].isna().sum())
 
@app.route('/')
def index():
    return send_from_directory('.', 'index.html')

 
@app.route('/api/data', methods=['GET'])
def get_data():
    global session_df
    return jsonify({
        "rows":      df_to_records(session_df),
        "nan_count": count_nan(session_df),
        "row_count": len(session_df),
    })

 
@app.route('/api/add-row', methods=['POST'])
def add_row():
    global session_df
    body = request.get_json()

    try:
        day  = int(body.get("day"))
        temp = body.get("temperature")
        hum  = body.get("humidity")

        temp = float(temp) if temp not in (None, "", "nan", "NaN") else None
        hum  = float(hum)  if hum  not in (None, "", "nan", "NaN") else None

        new_row = pd.DataFrame([{"day": day, "temperature": temp, "humidity": hum}])
        session_df = pd.concat([session_df, new_row], ignore_index=True)
        session_df = session_df.sort_values("day").reset_index(drop=True)

        return jsonify({
            "success":   True,
            "rows":      df_to_records(session_df),
            "nan_count": count_nan(session_df),
            "row_count": len(session_df),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 400

@app.route('/api/delete-row', methods=['POST'])
def delete_row():
    global session_df
    body = request.get_json()
    day  = int(body.get("day"))
    session_df = session_df[session_df["day"] != day].reset_index(drop=True)
    return jsonify({
        "success":   True,
        "rows":      df_to_records(session_df),
        "nan_count": count_nan(session_df),
        "row_count": len(session_df),
    })

 
@app.route('/api/reset', methods=['POST'])
def reset_data():
    global session_df
    session_df = pd.DataFrame(DEFAULT_DATA)
    return jsonify({
        "success":   True,
        "rows":      df_to_records(session_df),
        "nan_count": count_nan(session_df),
        "row_count": len(session_df),
    })

 
@app.route('/api/upload', methods=['POST'])
def upload_csv():
    global session_df
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    file = request.files['file']
    if not file.filename.endswith('.csv'):
        return jsonify({"error": "Only CSV files are supported"}), 400
    try:
        df = pd.read_csv(file)
        df.columns = [c.strip().lower() for c in df.columns]

 
        required = {"day", "temperature", "humidity"}
        if not required.issubset(set(df.columns)):
            return jsonify({"error": f"CSV must have columns: day, temperature, humidity. Found: {list(df.columns)}"}), 400

        df["day"]         = pd.to_numeric(df["day"],         errors="coerce")
        df["temperature"] = pd.to_numeric(df["temperature"], errors="coerce")
        df["humidity"]    = pd.to_numeric(df["humidity"],    errors="coerce")
        df = df.dropna(subset=["day"]).sort_values("day").reset_index(drop=True)
        df["day"] = df["day"].astype(int)

        session_df = df[["day", "temperature", "humidity"]]

        return jsonify({
            "success":   True,
            "rows":      df_to_records(session_df),
            "nan_count": count_nan(session_df),
            "row_count": len(session_df),
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

 
@app.route('/api/interpolate', methods=['POST', 'OPTIONS'])
def interpolate():
    if request.method == 'OPTIONS':
        return '', 200

    global session_df
    body   = request.get_json()
    method = body.get("method", "linear")

    df = session_df.copy()
    was_nan_temp = df["temperature"].isna().tolist()
    was_nan_hum  = df["humidity"].isna().tolist()

    if method == "linear":
        df["temperature"] = df["temperature"].interpolate(method="linear")
        df["humidity"]    = df["humidity"].interpolate(method="linear")
    elif method == "ffill":
        df["temperature"] = df["temperature"].ffill()
        df["humidity"]    = df["humidity"].ffill()
    elif method == "bfill":
        df["temperature"] = df["temperature"].bfill()
        df["humidity"]    = df["humidity"].bfill()
    elif method == "mean":
        df["temperature"] = df["temperature"].fillna(round(df["temperature"].mean(), 1))
        df["humidity"]    = df["humidity"].fillna(round(df["humidity"].mean(), 1))
    else:
        return jsonify({"error": f"Unknown method: {method}"}), 400

    records = []
    for i, row in df.iterrows():
        records.append({
            "day":         int(row["day"]),
            "temperature": round(float(row["temperature"]), 1) if not pd.isna(row["temperature"]) else None,
            "humidity":    round(float(row["humidity"]), 1)    if not pd.isna(row["humidity"])    else None,
            "temp_filled": bool(was_nan_temp[i]),
            "hum_filled":  bool(was_nan_hum[i]),
        })

    total_filled = sum(was_nan_temp) + sum(was_nan_hum)
    non_null_temps = [x for x in session_df["temperature"] if x is not None and not (isinstance(x, float) and np.isnan(x))]
    non_null_hums  = [x for x in session_df["humidity"]    if x is not None and not (isinstance(x, float) and np.isnan(x))]

    return jsonify({
        "method":       method,
        "rows":         records,
        "total_filled": total_filled,
        "stats": {
            "temp_mean": round(float(np.mean(non_null_temps)), 1) if non_null_temps else 0,
            "hum_mean":  round(float(np.mean(non_null_hums)),  1) if non_null_hums  else 0,
        }
    })

if __name__ == '__main__':
    print("\n  DataFill Flask Server")
    print("  ─────────────────────────────")
    print("  Open: http://localhost:5000")
    print("  Press CTRL+C to stop\n")
    app.run(debug=True, port=5000)