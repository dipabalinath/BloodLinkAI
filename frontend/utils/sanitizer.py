import numpy as np
import pandas as pd
from typing import Any
import logging

def sanitize_for_json(obj: Any) -> Any:
    """
    Recursively convert NumPy and Pandas data types to native Python types
    to ensure JSON serialization compatibility.
    """
    try:
        if isinstance(obj, (np.integer, int)):
            return int(obj)
        elif isinstance(obj, (np.floating, float)):
            return float(obj)
        elif isinstance(obj, (np.bool_, bool)):
            return bool(obj)
        elif isinstance(obj, np.ndarray):
            return [sanitize_for_json(item) for item in obj]
        elif isinstance(obj, (pd.Timestamp, np.datetime64)):
            return str(obj)
        elif isinstance(obj, dict):
            return {k: sanitize_for_json(v) for k, v in obj.items()}
        elif isinstance(obj, list):
            return [sanitize_for_json(item) for item in obj]
        elif isinstance(obj, tuple):
            return tuple(sanitize_for_json(item) for item in obj)
        return obj
    except Exception as e:
        logging.error(f"Serialization failed for field: {obj} | Error: {e}")
        return str(obj)

def safe_float(value: Any, default: float = 0.0) -> float:
    """
    Safely convert any value (None, NaN, numpy types, strings) into a valid float.
    Returns the default value if conversion fails or if the value is None/NaN.
    """
    if value is None:
        return default
    try:
        f_val = float(value)
        if np.isnan(f_val):
            return default
        return f_val
    except (ValueError, TypeError):
        return default
