import re


def safe_filename(value: str, fallback: str = "unknown") -> str:
    value = (value or fallback).strip()
    value = re.sub(r"[^\w\-]+", "_", value, flags=re.UNICODE)
    return value.strip("_") or fallback
