# DataFill — Python Interpolation Tool

A Flask + Pandas web app that fills missing dataset values via real Python interpolation.

## Project Structure

```
datafill_project/
├── app.py            ← Flask backend (Python + Pandas logic)
├── index.html        ← Frontend (calls Flask API)
├── requirements.txt  ← Python dependencies
└── README.md
```

## Setup & Run

### Step 1 — Install Python dependencies
```bash
pip install -r requirements.txt
```

### Step 2 — Start the Flask server
```bash
python app.py
```

### Step 3 — Open in browser
```
http://localhost:5000
```

That's it! The frontend is served by Flask itself.

## API Endpoints

| Method | Endpoint            | Description                        |
|--------|---------------------|------------------------------------|
| GET    | `/api/data`         | Returns the original dataset       |
| POST   | `/api/interpolate`  | Runs interpolation, returns result |
| POST   | `/api/upload`       | Upload your own CSV file           |

### POST /api/interpolate — Request Body
```json
{ "method": "linear" }
```
Methods: `linear` | `ffill` | `bfill` | `mean`

### POST /api/interpolate — Response
```json
{
  "method": "linear",
  "total_filled": 4,
  "rows": [
    { "day": 1, "temperature": 22.0, "humidity": 60.0, "temp_filled": false, "hum_filled": false },
    { "day": 2, "temperature": 23.5, "humidity": 63.0, "temp_filled": true,  "hum_filled": false },
    ...
  ]
}
```

## Interpolation Methods

| Method    | Pandas call                          | Best for                        |
|-----------|--------------------------------------|---------------------------------|
| Linear    | `.interpolate(method='linear')`      | Time-series with smooth trends  |
| Ffill     | `.ffill()`                           | Categorical / step-change data  |
| Bfill     | `.bfill()`                           | When future context is known    |
| Mean fill | `.fillna(df['col'].mean())`          | No temporal structure           |
