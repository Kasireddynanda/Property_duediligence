"""Export scraped RERA data to CSV or Excel."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import pandas as pd


def flatten_record(record: dict[str, Any]) -> dict[str, Any]:
    flat: dict[str, Any] = {}
    for key, value in record.items():
        if isinstance(value, dict):
            for sub_key, sub_value in value.items():
                if isinstance(sub_value, dict):
                    for inner_key, inner_value in sub_value.items():
                        flat[f"{key}.{sub_key}.{inner_key}"] = inner_value
                else:
                    flat[f"{key}.{sub_key}"] = sub_value
        elif isinstance(value, list):
            flat[key] = json.dumps(value, ensure_ascii=False)
        else:
            flat[key] = value
    return flat


def save_records(records: list[dict[str, Any]], output_path: str | Path) -> Path:
    path = Path(output_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    flat_records = [flatten_record(record) for record in records]
    df = pd.DataFrame(flat_records)

    if path.suffix.lower() == ".xlsx":
        df.to_excel(path, index=False)
    else:
        if path.suffix.lower() != ".csv":
            path = path.with_suffix(".csv")
        df.to_csv(path, index=False)

    return path
