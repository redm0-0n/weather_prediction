import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv(
    "API_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

LOCATIONS = {
    "innopolis": {
        "name": "Innopolis",
        "latitude": 55.752,
        "longitude": 48.744,
    },
    "kazan": {
        "name": "Kazan",
        "latitude": 55.796,
        "longitude": 49.106,
    },
    "cheboksary": {
        "name": "Cheboksary",
        "latitude": 56.143,
        "longitude": 47.248,
    },
    "ulyanovsk": {
        "name": "Ulyanovsk",
        "latitude": 54.314,
        "longitude": 48.403,
    },
    "yoshkar_ola": {
        "name": "Yoshkar-Ola",
        "latitude": 56.634,
        "longitude": 47.899,
    },
}

CURRENT_VARIABLES = [
    "temperature_2m",
    "relative_humidity_2m",
    "pressure_msl",
    "wind_speed_10m",
    "wind_direction_10m",
    "precipitation",
    "cloud_cover",
]

TABLE_TO_FEATURE = {
    "Temperature, °C": "temperature",
    "Humidity, %": "humidity",
    "Pressure, hPa": "pressure",
    "Wind speed, km/h": "wind_speed",
    "Wind direction, °": "wind_direction",
    "Precipitation, mm": "precipitation",
    "Cloud cover, %": "cloud_cover",
}


st.set_page_config(
    page_title="Innopolis Weather Forecast",
    layout="wide"
)


@st.cache_data(ttl=300)
def load_current_weather():
    rows = []

    for city, location in LOCATIONS.items():
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                "current": ",".join(CURRENT_VARIABLES),
                "timezone": "Europe/Moscow",
            },
            timeout=30,
        )
        response.raise_for_status()

        current = response.json()["current"]

        rows.append(
            {
                "City": location["name"],
                "Temperature, °C": float(
                    current["temperature_2m"]
                ),
                "Humidity, %": float(
                    current["relative_humidity_2m"]
                ),
                "Pressure, hPa": float(
                    current["pressure_msl"]
                ),
                "Wind speed, km/h": float(
                    current["wind_speed_10m"]
                ),
                "Wind direction, °": float(
                    current["wind_direction_10m"]
                ),
                "Precipitation, mm": float(
                    current["precipitation"]
                ),
                "Cloud cover, %": float(
                    current["cloud_cover"]
                ),
            }
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_model_info():
    response = requests.get(
        f"{API_URL}/model-info",
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def create_model_features(weather_df, required_features):
    features = {}

    for city, (_, row) in zip(
        LOCATIONS,
        weather_df.iterrows(),
    ):
        for table_column, feature_suffix in TABLE_TO_FEATURE.items():
            feature_name = f"{city}_{feature_suffix}"
            features[feature_name] = float(row[table_column])

    current_time = datetime.now(ZoneInfo("Europe/Moscow"))

    features["hour"] = float(current_time.hour)
    features["day_of_week"] = float(current_time.weekday())
    features["month"] = float(current_time.month)

    missing_features = set(required_features) - set(features)
    unexpected_features = set(features) - set(required_features)

    if missing_features or unexpected_features:
        raise ValueError(
            {
                "missing_features": sorted(missing_features),
                "unexpected_features": sorted(unexpected_features),
            }
        )

    return {
        feature: features[feature]
        for feature in required_features
    }


def request_prediction(features):
    response = requests.post(
        f"{API_URL}/predict",
        json={"features": features},
        timeout=30,
    )

    if not response.ok:
        raise RuntimeError(
            f"API returned {response.status_code}: {response.text}"
        )

    return response.json()


st.title("Innopolis Weather Forecast")

st.write(
    "Prediction of the temperature in Innopolis "
    "three hours ahead."
)

try:
    model_info = load_model_info()
except requests.RequestException as error:
    st.error(
        "FastAPI is unavailable. Start the API on port 8000."
    )
    st.exception(error)
    st.stop()

refresh_column, status_column = st.columns([1, 3])

with refresh_column:
    if st.button(
        "Refresh weather",
        use_container_width=True,
    ):
        load_current_weather.clear()
        st.rerun()

with status_column:
    st.success(
        f"Model API is available. "
        f"Forecast horizon: "
        f"{model_info['prediction_horizon_hours']} hours."
    )

try:
    weather_df = load_current_weather()
except requests.RequestException as error:
    st.error("Could not load current weather from Open-Meteo.")
    st.exception(error)
    st.stop()

st.subheader("Current weather")

edited_weather = st.data_editor(
    weather_df,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    disabled=["City"],
    column_config={
        "City": st.column_config.TextColumn(
            "City",
        ),
        "Temperature, °C": st.column_config.NumberColumn(
            "Temperature, °C",
            format="%.1f",
        ),
        "Humidity, %": st.column_config.NumberColumn(
            "Humidity, %",
            min_value=0.0,
            max_value=100.0,
            format="%.0f",
        ),
        "Pressure, hPa": st.column_config.NumberColumn(
            "Pressure, hPa",
            min_value=850.0,
            max_value=1100.0,
            format="%.1f",
        ),
        "Wind speed, km/h": st.column_config.NumberColumn(
            "Wind speed, km/h",
            min_value=0.0,
            format="%.1f",
        ),
        "Wind direction, °": st.column_config.NumberColumn(
            "Wind direction, °",
            min_value=0.0,
            max_value=360.0,
            format="%.0f",
        ),
        "Precipitation, mm": st.column_config.NumberColumn(
            "Precipitation, mm",
            min_value=0.0,
            format="%.1f",
        ),
        "Cloud cover, %": st.column_config.NumberColumn(
            "Cloud cover, %",
            min_value=0.0,
            max_value=100.0,
            format="%.0f",
        ),
    },
)

st.caption(
    "The values are loaded automatically from Open-Meteo "
    "and can be edited before prediction."
)

if st.button(
    "Predict temperature in 3 hours",
    type="primary",
    use_container_width=True,
):
    try:
        features = create_model_features(
            edited_weather,
            model_info["features"],
        )

        with st.spinner("Calculating prediction..."):
            result = request_prediction(features)

        st.success("Prediction completed")

        result_column, time_column = st.columns(2)

        with result_column:
            st.metric(
                "Predicted temperature",
                f"{result['predicted_temperature']:.2f} °C",
            )

        with time_column:
            st.metric(
                "Forecast horizon",
                f"{result['prediction_horizon_hours']} hours",
            )

    except (
        requests.RequestException,
        RuntimeError,
        ValueError,
    ) as error:
        st.error("Prediction failed")
        st.exception(error)