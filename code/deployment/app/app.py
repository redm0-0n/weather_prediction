import os
from datetime import datetime
from zoneinfo import ZoneInfo

import pandas as pd
import requests
import streamlit as st


API_URL = os.getenv("API_URL", "http://127.0.0.1:8000").rstrip("/")
OPEN_METEO_URL = "https://api.open-meteo.com/v1/forecast"

LOCATIONS = {
    "innopolis": ("Innopolis", 55.752, 48.744),
    "kazan": ("Kazan", 55.796, 49.106),
    "cheboksary": ("Cheboksary", 56.143, 47.248),
    "ulyanovsk": ("Ulyanovsk", 54.314, 48.403),
    "yoshkar_ola": ("Yoshkar-Ola", 56.634, 47.899),
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

COLUMNS = {
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
    layout="wide",
)

st.markdown(
    """
    <style>
    [data-testid="stAppViewContainer"] {
        background: #f4f7fb;
        color: #243b53;
    }
    [data-testid="stHeader"] {
        background: #f4f7fb;
    }
    .block-container {
        max-width: 1180px;
        padding-top: 2.5rem;
        padding-bottom: 3rem;
    }
    h1, h2, h3 {
        color: #243b53;
    }
    .subtitle {
        color: #627d98;
        font-size: 1.05rem;
        margin-top: -0.7rem;
        margin-bottom: 1.8rem;
    }
    .status-box {
        background: #e7eef7;
        border: 1px solid #bcccdc;
        border-radius: 8px;
        color: #334e68;
        padding: 0.75rem 1rem;
        margin-bottom: 1rem;
    }
    .result-box {
        background: #d9e8f5;
        border: 1px solid #9fb3c8;
        border-radius: 10px;
        color: #243b53;
        padding: 1.4rem 1.6rem;
        margin-top: 1.2rem;
    }
    .result-value {
        color: #1f4e79;
        font-size: 2.2rem;
        font-weight: 700;
        margin: 0.25rem 0;
    }
    div.stButton > button {
        background: #486581;
        border: 1px solid #486581;
        color: white;
        border-radius: 7px;
    }
    div.stButton > button:hover {
        background: #334e68;
        border-color: #334e68;
        color: white;
    }
    </style>
    """,
    unsafe_allow_html=True,
)


@st.cache_data(ttl=300)
def load_current_weather():
    rows = []

    for _, (name, latitude, longitude) in LOCATIONS.items():
        response = requests.get(
            OPEN_METEO_URL,
            params={
                "latitude": latitude,
                "longitude": longitude,
                "current": ",".join(CURRENT_VARIABLES),
                "timezone": "Europe/Moscow",
            },
            timeout=30,
        )
        response.raise_for_status()
        current = response.json()["current"]

        rows.append(
            {
                "City": name,
                "Temperature, °C": float(current["temperature_2m"]),
                "Humidity, %": float(current["relative_humidity_2m"]),
                "Pressure, hPa": float(current["pressure_msl"]),
                "Wind speed, km/h": float(current["wind_speed_10m"]),
                "Wind direction, °": float(current["wind_direction_10m"]),
                "Precipitation, mm": float(current["precipitation"]),
                "Cloud cover, %": float(current["cloud_cover"]),
            }
        )

    return pd.DataFrame(rows)


@st.cache_data(ttl=60)
def load_model_info():
    response = requests.get(f"{API_URL}/model-info", timeout=10)
    response.raise_for_status()
    return response.json()


def create_features(weather, required_features):
    features = {}

    for city, (_, row) in zip(LOCATIONS, weather.iterrows()):
        for column, suffix in COLUMNS.items():
            features[f"{city}_{suffix}"] = float(row[column])

    current_time = datetime.now(ZoneInfo("Europe/Moscow"))
    features["hour"] = float(current_time.hour)
    features["day_of_week"] = float(current_time.weekday())
    features["month"] = float(current_time.month)

    return {name: features[name] for name in required_features}


def request_prediction(features):
    response = requests.post(
        f"{API_URL}/predict",
        json={"features": features},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()


st.title("Innopolis weather forecast")
st.markdown(
    '<div class="subtitle">Temperature prediction three hours ahead</div>',
    unsafe_allow_html=True,
)

try:
    model_info = load_model_info()
    weather = load_current_weather()
except requests.RequestException as error:
    st.error(f"Service is unavailable: {error}")
    st.stop()

header_left, header_right = st.columns([3, 1])

with header_left:
    updated_at = datetime.now(ZoneInfo("Europe/Moscow")).strftime(
        "%d.%m.%Y %H:%M MSK"
    )
    st.markdown(
        f'<div class="status-box">Weather updated: {updated_at}</div>',
        unsafe_allow_html=True,
    )

with header_right:
    if st.button("Refresh data", use_container_width=True):
        load_current_weather.clear()
        st.rerun()

st.subheader("Current weather")
st.write("Values are loaded from Open-Meteo. You can edit them before prediction.")

edited_weather = st.data_editor(
    weather,
    hide_index=True,
    use_container_width=True,
    num_rows="fixed",
    disabled=["City"],
    column_config={
        "Temperature, °C": st.column_config.NumberColumn(format="%.1f"),
        "Humidity, %": st.column_config.NumberColumn(
            min_value=0.0, max_value=100.0, format="%.0f"
        ),
        "Pressure, hPa": st.column_config.NumberColumn(
            min_value=850.0, max_value=1100.0, format="%.1f"
        ),
        "Wind speed, km/h": st.column_config.NumberColumn(
            min_value=0.0, format="%.1f"
        ),
        "Wind direction, °": st.column_config.NumberColumn(
            min_value=0.0, max_value=360.0, format="%.0f"
        ),
        "Precipitation, mm": st.column_config.NumberColumn(
            min_value=0.0, format="%.1f"
        ),
        "Cloud cover, %": st.column_config.NumberColumn(
            min_value=0.0, max_value=100.0, format="%.0f"
        ),
    },
)

st.divider()

if st.button(
    "Predict temperature",
    type="primary",
    use_container_width=True,
):
    try:
        features = create_features(edited_weather, model_info["features"])

        with st.spinner("Calculating prediction..."):
            result = request_prediction(features)

        st.markdown(
            f"""
            <div class="result-box">
                <div>Predicted temperature in Innopolis</div>
                <div class="result-value">{result['predicted_temperature']:.2f} °C</div>
                <div>Forecast horizon: {result['prediction_horizon_hours']} hours</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
    except (KeyError, requests.RequestException) as error:
        st.error(f"Prediction failed: {error}")
