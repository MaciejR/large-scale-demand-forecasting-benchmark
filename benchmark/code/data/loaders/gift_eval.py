"""
GIFT-Eval dataset loader — Sales domain subset.
Loads data into unified long-format [series_id, ds, y].
Requires: pip install salesforce-gift-eval
Data: huggingface-cli download Salesforce/GiftEval --repo-type=dataset --local-dir <path>
Set env: GIFT_EVAL=<path>
"""

import pandas as pd

SALES_DATASETS = [
    "car_parts_with_missing",
    "restaurant",
    "hierarchical_sales/D",
    "hierarchical_sales/W",
]


def load_gift_eval(
    dataset_name: str,
    term: str = "short",
) -> pd.DataFrame:
    """
    Load a GIFT-Eval dataset and convert to long format.

    Parameters
    ----------
    dataset_name : str
        One of SALES_DATASETS (e.g. "restaurant", "hierarchical_sales/W").
    term : str
        Prediction term: "short", "medium", or "long".

    Returns
    -------
    pd.DataFrame with columns [series_id, ds, y].
    """
    from gift_eval.data import Dataset

    ds = Dataset(name=dataset_name, term=term, to_univariate=True)

    records = []
    for entry in ds.training_dataset:
        item_id = entry["item_id"]
        start = entry["start"]
        freq = entry["freq"]
        target = entry["target"]

        dates = pd.period_range(
            start=start, periods=len(target), freq=freq
        ).to_timestamp()

        records.append(pd.DataFrame({
            "series_id": str(item_id),
            "ds": dates,
            "y": target.astype(float),
        }))

    return pd.concat(records, ignore_index=True)


def get_gift_eval_prediction_length(dataset_name: str, term: str = "short") -> int:
    """Get the prediction length for a given dataset and term."""
    from gift_eval.data import Dataset

    ds = Dataset(name=dataset_name, term=term, to_univariate=True)
    return ds.prediction_length
