import requesrs
import pandas as pd
from datetime import datetime, timezone
from pathlib import Path

API = "https://api.open-meteo.com/v1/forecast"

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

OUTPUT_PATH = Path("data/raw/weather.csv")

def get_weather(city_name, latitude, longitude):
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": [
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

    response = requests.get(
        API,
        params=params,
        timeout=10
    )
    response.raise_for_status()
    data = response.json()
    current = data["current"]

    return {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "city": city_name,
        "temperature": current["temperature_2m"],
        "humidity": current["relative_humidity_2m"],
        "pressure": current["pressure_msl"],
        "wind_speed": current["wind_speed_10m"],
        "wind_direction": current["wind_direction_10m"],
        "precipitation": current["precipitation"],
        "cloud_cover": current["cloud_cover"]
    }

def save_data(records):
    df_new = pd.DataFrame(records)

    OUTPUT_PATH.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    if OUTPUT_PATH.exists():
        df_old = pd.read_csv(OUTPUT_PATH)
        df = pd.concat([df_old, df_new], ignore_index=True)
    else:
        df = df_new

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"Saved {len(df_new)} new rows")
    print(f"Total rows: {len(df)}")

def main():
    records = []
    for city, coords in LOCATIONS.items():
        print(f"Collecting {city}...")
        weather = get_weather(
            city_name=city,
            latitude=coords["latitude"],
            longitude=coords["longitude"]
        )
        records.append(weather)

    save_data(records)

if __name__ == "__main__":
    main()
