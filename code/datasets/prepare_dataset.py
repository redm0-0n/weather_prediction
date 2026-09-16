import pandas as pd
from pathlib import Path
from sklearn.model_selection import train_test_split

INPUT = Path("data/raw/weather_history.csv")
TRAIN_OUTPUT = Path("data/processed/train.csv")
TEST_OUTPUT = Path("data/processed/test.csv")
TARGET_CITY = "innopolis"

def load_data():
    df = pd.read_csv(INPUT, parse_dates=["datetime"])
    return df

def pivot_weather(df):
    features = [
        "temperature",
        "humidity",
        "pressure",
        "wind_speed",
        "wind_direction",
        "precipitation",
        "cloud_cover"
    ]
    df = df.pivot(index="datetime", columns="city", values=features)
    df.columns = [f"{city}_{feature}" for feature, city in df.columns]
    df.reset_index(inplace=True)
    return df

def create_target(df):
    target_column = ("innopolis_temperature")
    df["target_temperature_3h"] = (df[target_column] .shift(-3))
    return df

def add_time_features(df):
    df["hour"] = (df.datetime.dt.hour)
    df["day_of_week"] = (df.datetime.dt.dayofweek)
    df["month"] = (df.datetime.dt.month)
    return df

def clean(df):
    df = df.dropna()
    return df

def split(df):
    X = df.drop(columns=["target_temperature_3h"])
    y = df["target_temperature_3h"]
    train_X, test_X, train_y, test_y = train_test_split(X, y, test_size=0.2, random_state=42, shuffle=False)
    train = train_X.copy()
    train["target_temperature_3h"] = train_y
    test = test_X.copy()
    test["target_temperature_3h"] = test_y
    return train, test

def main():
    df = load_data()
    df = pivot_weather(df)
    df = create_target(df)
    df = add_time_features(df)
    df = clean(df)

    train, test = split(df)
    TRAIN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    train.to_csv(TRAIN_OUTPUT, index=False)
    test.to_csv(TEST_OUTPUT, index=False)
    print("Train:", train.shape)
    print("Test:", test.shape)

if __name__ == "__main__":
    main()