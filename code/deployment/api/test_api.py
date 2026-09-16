from pathlib import Path
import pandas as pd
import requests

PROJECT_ROOT = Path(__file__).resolve().parents[3]
TEST_DATA_PATH = PROJECT_ROOT / "data" / "processed" / "test.csv"
API_URL = "http://127.0.0.1:8000/predict"
TARGET_COLUMN = "target_temperature_3h"
DATETIME_COLUMN = "datetime"

def main():
    test_df = pd.read_csv(TEST_DATA_PATH)
    test_row = test_df.iloc[0]
    actual_temperature = float(test_row[TARGET_COLUMN])
    
    feature_values = test_row.drop(labels=[DATETIME_COLUMN, TARGET_COLUMN])
    features = {name: float(value) for name, value in feature_values.items()}

    response = requests.post(API_URL, json={"features": features}, timeout=30)
    print("HTTP status:", response.status_code)

    if response.ok:
        result = response.json()

        print(
            "Predicted temperature:",
            round(result["predicted_temperature"], 2),
            "°C",
        )
        print(
            "Actual temperature:",
            round(actual_temperature, 2),
            "°C",
        )
        print(
            "Absolute error:",
            round(
                abs(
                    result["predicted_temperature"]
                    - actual_temperature
                ),
                2,
            ),
            "°C",
        )
    else:
        print("API error:")
        print(response.text)

if __name__ == "__main__":
    main()