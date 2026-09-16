import requests
import pandas as pd
from pathlib import Path
from datetime import datetime, date, timedelta

END_DATE = date.today() - timedelta(days=5)
START_DATE = END_DATE - timedelta(days=365)
START_DATE = START_DATE.isoformat()
END_DATE = END_DATE.isoformat()
LOCATIONS = {
    "innopolis": {
        "latitude": 55.752,
        "longitude": 48.744
    },
    "kazan": {
        "latitude": 55.796,
        "longitude": 49.106
    },
    "cheboksary": {
        "latitude": 56.143,
        "longitude": 47.248
    },
    "ulyanovsk": {
        "latitude": 54.314,
        "longitude": 48.403
    },
    "yoshkar_ola": {
        "latitude": 56.634,
        "longitude": 47.899
    }
}

API = ("https://archive-api.open-meteo.com/v1/archive")
OUTPUT = Path("data/raw/weather_history.csv")

def get_history(city, lat, lon):
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": START_DATE,
        "end_date": END_DATE,
        "hourly": [
            "temperature_2m",
            "relative_humidity_2m",
            "pressure_msl",
            "wind_speed_10m",
            "wind_direction_10m",
            "precipitation",
            "cloud_cover"
        ],
        "timezone": "Europe/Moscow"
    }

    response = requests.get(API, params=params, timeout=30)
    response.raise_for_status()
    data = response.json()
    hourly = data["hourly"]
    df = pd.DataFrame(hourly)
    df["city"] = city
    return df

def main():
    all_data = []
    for city, coords in LOCATIONS.items():
        print(f"Downloading {city}")
        df = get_history(city, coords["latitude"], coords["longitude"])
        all_data.append(df)

    result = pd.concat(all_data, ignore_index=True)
    result.rename(
        columns={
            "time": "datetime",
            "temperature_2m": "temperature",
            "relative_humidity_2m": "humidity",
            "pressure_msl": "pressure",
            "wind_speed_10m": "wind_speed",
            "wind_direction_10m": "wind_direction"
        },
        inplace=True
    )
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(OUTPUT, index=False)
    print("Saved:", OUTPUT)
    print("Rows:", len(result))

if __name__ == "__main__":
    main()