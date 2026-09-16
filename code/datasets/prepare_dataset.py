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
    df = df.replace([float("inf"), float("-inf")], pd.NA)
    rows_before = len(df)
    df = df.dropna().copy()
    rows_removed = rows_before - len(df)
    print(f"Rows removed because of missing values: {rows_removed}")
    return df


def remove_outliers(df):
    df = df.copy()
    rows_before = len(df)
    valid_mask = pd.Series(True, index=df.index)

    for column in df.columns:
        if column.endswith("_humidity"):
            valid_mask &= df[column].between(0, 100)
        elif column.endswith("_cloud_cover"):
            valid_mask &= df[column].between(0, 100)
        elif column.endswith("_wind_direction"):
            valid_mask &= df[column].between(0, 360)
        elif column.endswith("_precipitation"):
            valid_mask &= df[column] >= 0
        elif column.endswith("_wind_speed"):
            valid_mask &= df[column] >= 0
        elif column.endswith("_pressure"):
            valid_mask &= df[column].between(850, 1100)

    df = df.loc[valid_mask].copy()
    iqr_columns = [
        column
        for column in df.columns
        if (
            column.endswith("_temperature")
            or column.endswith("_pressure")
            or column.endswith("_wind_speed")
        )
    ]
    outlier_mask = pd.Series(False, index=df.index)

    for column in iqr_columns:
        q1 = df[column].quantile(0.25)
        q3 = df[column].quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            continue

        lower_bound = q1 - 3 * iqr
        upper_bound = q3 + 3 * iqr

        outlier_mask |= ~df[column].between(lower_bound, upper_bound)

    df = df.loc[~outlier_mask].copy()

    rows_removed = rows_before - len(df)
    print(f"Rows removed as outliers: {rows_removed}")

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
    df = remove_outliers(df)

    train, test = split(df)
    TRAIN_OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    train.to_csv(TRAIN_OUTPUT, index=False)
    test.to_csv(TEST_OUTPUT, index=False)
    print("Train:", train.shape)
    print("Test:", test.shape)

if __name__ == "__main__":
    main()