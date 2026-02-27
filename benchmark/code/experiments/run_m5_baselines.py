"""
Run baseline models on the M5 dataset.
"""

from data.loaders.m5 import load_m5
from models.baselines.naive import naive_forecast
from models.baselines.ets import ets_forecast
from evaluation.rolling import rolling_forecast
from evaluation.metrics import aggregate_metrics


DATA_PATH = "data/m5/"


def main():
    df = load_m5(
        f"{DATA_PATH}/sales_train_validation.csv",
        f"{DATA_PATH}/calendar.csv",
    )

    horizon = 7
    min_train_size = 100

    print("Running Naive baseline...")
    naive_res = rolling_forecast(df, horizon, min_train_size, naive_forecast)
    naive_metrics = aggregate_metrics(naive_res)

    print("Running ETS baseline...")
    ets_res = rolling_forecast(df, horizon, min_train_size, ets_forecast)
    ets_metrics = aggregate_metrics(ets_res)

    print("Naive results:")
    print(naive_metrics.describe())

    print("ETS results:")
    print(ets_metrics.describe())

    # LightGBM global model
    from models.ml.lightgbm import LightGBMForecaster

    print("Running LightGBM global model...")
    lgbm = LightGBMForecaster()
    lgbm.fit(df)

    def lgbm_wrapper(train, horizon):
        hist = df[df["series_id"] == train.name][["series_id", "ds", "y"]]
        return lgbm.predict(hist, horizon)

    lgbm_res = rolling_forecast(df, horizon, min_train_size, lgbm_wrapper)
    lgbm_metrics = aggregate_metrics(lgbm_res)

    print("LightGBM results:")
    print(lgbm_metrics.describe())


if __name__ == "__main__":
    main()
