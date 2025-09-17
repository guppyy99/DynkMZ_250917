
import os
import json
from datetime import date
from typing import List, Dict, Any
import requests
import pandas as pd
import matplotlib.pyplot as plt

# ------------------ CONFIG ------------------
START_DATE = "2024-01-01"
END_DATE   = "2024-12-31"
TIMEZONE   = "Asia/Seoul"
# Seoul as a proxy for KR nationwide. Adjust if needed.
LATITUDE   = 37.5665
LONGITUDE  = 126.9780

KEYWORDS = [
    {"groupName": "라운딩", "keywords": ["라운딩"]},
    {"groupName": "골프 예약", "keywords": ["골프 예약"]},
    {"groupName": "골프 부킹", "keywords": ["골프 부킹"]},
    {"groupName": "골프장", "keywords": ["골프장"]},
]

# Rain/Snow thresholds (mm)
RAIN_MM_THRESHOLD = 1.0
SNOW_MM_THRESHOLD = 1.0

# Output paths
OUT_DAILY_CSV      = "naver_golf_trend_weather_daily_2024.csv"
OUT_SUMMARY_CSV    = "naver_golf_trend_weather_summary_2024.csv"
OUT_BAR_PNG        = "naver_golf_trend_by_weather_2024.png"

# --------------- Helper Functions ---------------

def fetch_naver_datalab_daily(keyword_groups: List[Dict[str, Any]], start_date: str, end_date: str) -> pd.DataFrame:
    """
    Calls Naver DataLab Search Trend (daily) and returns a DataFrame:
    columns: [date, group, ratio]
    """
    url = "https://openapi.naver.com/v1/datalab/search"
    headers = {
        "X-Naver-Client-Id": os.environ["NAVER_CLIENT_ID"],
        "X-Naver-Client-Secret": os.environ["NAVER_CLIENT_SECRET"],
        "Content-Type": "application/json",
    }
    body = {
        "startDate": start_date,
        "endDate": end_date,
        "timeUnit": "date",       # daily
        "keywordGroups": keyword_groups,
    }
    resp = requests.post(url, headers=headers, data=json.dumps(body), timeout=60)
    resp.raise_for_status()
    data = resp.json()

    rows = []
    for group in data.get("results", []):
        gname = group["title"]
        for item in group["data"]:
            rows.append({
                "date": item["period"],
                "group": gname,
                "ratio": item["ratio"]
            })
    df = pd.DataFrame(rows)
    df["date"] = pd.to_datetime(df["date"]).dt.date
    return df

def fetch_open_meteo_daily(lat: float, lon: float, start_date: str, end_date: str, tz: str) -> pd.DataFrame:
    """
    Fetches daily precipitation/rain/snow from Open-Meteo Historical Weather API.
    """
    base_url = "https://archive-api.open-meteo.com/v1/archive"
    params = {
        "latitude": lat,
        "longitude": lon,
        "start_date": start_date,
        "end_date": end_date,
        "daily": "precipitation_sum,rain_sum,snowfall_sum",
        "timezone": tz,
    }
    r = requests.get(base_url, params=params, timeout=60)
    r.raise_for_status()
    js = r.json()
    daily = js.get("daily", {})
    df = pd.DataFrame({
        "date": pd.to_datetime(daily.get("time", [])).date,
        "precipitation_sum": daily.get("precipitation_sum", []),
        "rain_sum": daily.get("rain_sum", []),
        "snowfall_sum": daily.get("snowfall_sum", []),
    })
    return df

def classify_weather(row) -> str:
    rain = row.get("rain_sum", 0.0) or 0.0
    snow = row.get("snowfall_sum", 0.0) or 0.0
    if rain >= RAIN_MM_THRESHOLD and snow >= SNOW_MM_THRESHOLD:
        return "mixed"
    if snow >= SNOW_MM_THRESHOLD:
        return "snow"
    if rain >= RAIN_MM_THRESHOLD:
        return "rain"
    return "dry"

def analyze(df_trend: pd.DataFrame, df_wx: pd.DataFrame):
    """
    Merge trend and weather; compute mean ratios by weather type and deltas vs dry.
    Returns (daily_merged, summary)
    """
    merged = pd.merge(df_trend, df_wx, on="date", how="inner")
    merged["day_type"] = merged.apply(classify_weather, axis=1)

    summary = (
        merged.groupby(["group", "day_type"])["ratio"]
        .mean()
        .reset_index()
        .pivot(index="group", columns="day_type", values="ratio")
        .fillna(0.0)
    )
    # add delta columns vs dry
    for t in ["rain", "snow", "mixed"]:
        if "dry" in summary.columns:
            summary[f"{t}_vs_dry"] = summary.get(t, 0.0) - summary["dry"]
    summary = summary.reset_index()

    return merged, summary

def plot_bar(summary: pd.DataFrame, out_png: str):
    """
    Simple bar chart: avg ratio by weather type per group.
    """
    # Melt for plotting
    keep = ["group"]
    weather_cols = [c for c in ["dry","rain","snow","mixed"] if c in summary.columns]
    dfm = summary[keep + weather_cols].melt(id_vars="group", var_name="day_type", value_name="avg_ratio")
    plt.figure(figsize=(10,6))
    # Do not set any colors
    for grp in dfm["group"].unique():
        sub = dfm[dfm["group"] == grp]
        plt.bar(sub["day_type"] + " (" + grp + ")", sub["avg_ratio"])
    plt.title("Naver Search Ratio by Weather Type (2024, KR, Seoul proxy)")
    plt.xlabel("Weather Type (per keyword)")
    plt.ylabel("Average Search Ratio (relative index)")
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(out_png, dpi=150)
    plt.close()

def main():
    # Fetch data
    print("[1/4] Fetching Naver DataLab daily trends...")
    df_trend = fetch_naver_datalab_daily(KEYWORDS, START_DATE, END_DATE)
    print(f"  -> {len(df_trend):,} rows")

    print("[2/4] Fetching Open-Meteo daily weather (Seoul proxy)...")
    df_wx = fetch_open_meteo_daily(LATITUDE, LONGITUDE, START_DATE, END_DATE, TIMEZONE)
    print(f"  -> {len(df_wx):,} rows")

    print("[3/4] Merging & analyzing...")
    daily, summary = analyze(df_trend, df_wx)

    # Save outputs
    print("[4/4] Saving outputs...")
    daily.to_csv(OUT_DAILY_CSV, index=False, encoding="utf-8-sig")
    summary.to_csv(OUT_SUMMARY_CSV, index=False, encoding="utf-8-sig")
    plot_bar(summary, OUT_BAR_PNG)

    print("\nDone.")
    print(f"- Daily merged CSV: {OUT_DAILY_CSV}")
    print(f"- Summary CSV:      {OUT_SUMMARY_CSV}")
    print(f"- Chart:            {OUT_BAR_PNG}")

if __name__ == "__main__":
    main()
