"""
Аудит временного покрытия всех индикаторов по 48 юрисдикциям.
Для каждой юрисдикции × серии показывает: доступные года, год последнего значения,
разброс свежести данных.

Результат: CSV-таблица с value + year для каждого фактора.
"""
import json
import os
import sys

import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "03_data", "jurisdictions_registry.json")

with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    JURISDICTIONS = {j["name_en"]: j for j in json.load(f)}
TARGET = set(JURISDICTIONS.keys())

NAME_MAP = {
    "Korea, Rep.": "South Korea",
    "Hong Kong SAR, China": "Hong Kong",
    "Hong Kong, China": "Hong Kong",
    "Turkiye": "Turkey",
    "Türkiye": "Turkey",
    "Czech Republic": "Czech Republic",
    "Czechia": "Czech Republic",
    "Russian Federation": "Russia",
    "Egypt, Arab Rep.": "Egypt",
    "Taiwan, China": "Taiwan",
    "United States - New York City": "United States",
    "United States - Los Angeles": "United States",
    "China - Beijing": "China",
    "China - Shanghai": "China",
}

def norm(name):
    if pd.isna(name):
        return None
    s = str(name).strip().rstrip("*")
    return NAME_MAP.get(s, s)

def extract_year(col_name):
    """'2019 [YR2019]' -> 2019"""
    return int(col_name.split("[")[0].strip())

def latest_per_country(df, yr_cols):
    """Return DataFrame with value, year, and availability map per country."""
    records = []
    for _, row in df.iterrows():
        country = norm(row.get("Country Name") or row.get("Location"))
        if country is None or country not in TARGET:
            continue

        avail_years = []
        latest_val = np.nan
        latest_yr = None
        for yc in reversed(yr_cols):
            raw = row[yc]
            if str(raw).strip() in ("..", "") or pd.isna(raw):
                continue
            try:
                v = float(raw)
            except (ValueError, TypeError):
                continue
            yr = extract_year(yc)
            avail_years.append(yr)
            if pd.isna(latest_val):
                latest_val = v
                latest_yr = yr

        records.append({
            "country": country,
            "value": latest_val,
            "year": latest_yr,
            "available_years": sorted(avail_years),
            "n_years": len(avail_years),
        })

    result = pd.DataFrame(records)
    if not result.empty:
        result = result.drop_duplicates(subset="country", keep="first")
    return result


# =====================================================================
# 1. F2 — Doing Business (fixed date: May 1, 2019)
# =====================================================================
print("=" * 80)
print("F2: Protecting Minority Investors — Doing Business 2020 (data as of 01.05.2019)")
print("=" * 80)

f2_path = os.path.join(DATA_DIR, "F2 - Protecting Minority Investors.xlsx")
f2_df = pd.read_excel(f2_path, sheet_name="Sheet1")
f2_df = f2_df[f2_df["Location"].notna()].copy()
f2_df["country"] = f2_df["Location"].apply(norm)
f2_df = f2_df.drop_duplicates(subset="country", keep="first")
f2_target = f2_df[f2_df["country"].isin(TARGET)]
print(f"Coverage: {len(f2_target)}/48 jurisdictions")
print("Fixed reference date: 2019-05-01 (no temporal variation)")
print()

# =====================================================================
# 2. F4-F6 — WGI (5-year intervals: 2004, 2009, 2014, 2019, 2024)
# =====================================================================
print("=" * 80)
print("F4-F6: WGI — Regulatory Quality, Rule of Law, Political Stability")
print("=" * 80)

wgi_path = os.path.join(DATA_DIR, "F4-6 P_Data_Extract_From_Worldwide_Governance_Indicators.xlsx")
wgi_df = pd.read_excel(wgi_path, sheet_name="Data")
wgi_df = wgi_df[wgi_df["Country Code"].notna()].copy()
wgi_df["country"] = wgi_df["Country Name"].apply(norm)

wgi_yr_cols = [c for c in wgi_df.columns if "[YR" in str(c)]
wgi_series = {
    "GOV_WGI_RQ.EST": "F4_regulatory_quality",
    "GOV_WGI_RL.EST": "F5_rule_of_law",
    "GOV_WGI_PV.EST": "F6_political_stability",
}

print(f"Year columns: {[extract_year(c) for c in wgi_yr_cols]}")
print(f"Regular 5-year intervals -> supports trend analysis")
print()

for code, name in wgi_series.items():
    subset = wgi_df[wgi_df["Series Code"] == code]
    target_subset = subset[subset["country"].isin(TARGET)]

    print(f"  {name} ({code}):")
    for yc in wgi_yr_cols:
        yr = extract_year(yc)
        vals = target_subset[yc].replace("..", pd.NA)
        vals = pd.to_numeric(vals, errors="coerce")
        n = vals.notna().sum()
        print(f"    {yr}: {n}/48")
    print()


# =====================================================================
# 3. F7 + additional — WDI (annual, but spotty for some countries)
# =====================================================================
print("=" * 80)
print("F7+: WDI — Market cap/GDP, Listed companies, Savings")
print("=" * 80)

wdi_path = os.path.join(DATA_DIR, "F7 P_Data_Extract_From_World_Development_Indicators.xlsx")
wdi_df = pd.read_excel(wdi_path, sheet_name="Data")
wdi_df = wdi_df[wdi_df["Country Code"].notna()].copy()
wdi_df["country"] = wdi_df["Country Name"].apply(norm)

wdi_yr_cols = [c for c in wdi_df.columns if "[YR" in str(c)]
wdi_series_map = {
    "CM.MKT.LCAP.GD.ZS": "F7_market_cap_pct_gdp",
    "CM.MKT.LCAP.CD":    "F7x_market_cap_usd",
    "CM.MKT.LDOM.NO":    "F7x_listed_companies",
    "NY.GDS.TOTL.ZS":    "Fx_savings_pct_gdp",
    "NY.GDS.TOTL.CD":    "Fx_savings_usd",
}

all_wdi_results = {}

for series_code, factor_label in wdi_series_map.items():
    subset = wdi_df[wdi_df["Series Code"] == series_code].copy()
    audit = latest_per_country(subset, wdi_yr_cols)

    print(f"\n--- {factor_label} ({series_code}) ---")

    if audit.empty:
        print("  No data for target jurisdictions!")
        continue

    n_with_data = audit["value"].notna().sum()
    missing = TARGET - set(audit["country"])
    no_data = set(audit[audit["value"].isna()]["country"])
    total_missing = missing | no_data

    print(f"  Jurisdictions with data: {n_with_data}/48")
    if total_missing:
        print(f"  Missing: {sorted(total_missing)}")

    if n_with_data > 0:
        year_dist = audit[audit["year"].notna()]["year"].value_counts().sort_index()
        print(f"  Year distribution of latest values:")
        for yr, cnt in year_dist.items():
            countries = sorted(audit[audit["year"] == yr]["country"].tolist())
            print(f"    {int(yr)}: {cnt} countries — {countries}")

        min_yr = int(audit["year"].min()) if audit["year"].notna().any() else None
        max_yr = int(audit["year"].max()) if audit["year"].notna().any() else None
        if min_yr and max_yr:
            spread = max_yr - min_yr
            print(f"  Year spread: {min_yr}–{max_yr} ({spread} years)")

    all_wdi_results[factor_label] = audit


# =====================================================================
# Summary: temporal alignment assessment
# =====================================================================
print("\n" + "=" * 80)
print("TEMPORAL ALIGNMENT ASSESSMENT")
print("=" * 80)

print("""
Source data characteristics:

1. F2 (Doing Business):
   - FIXED DATE: 2019-05-01
   - No temporal variation between countries
   - Programme discontinued (no updates possible)

2. F4-F6 (WGI):
   - REGULAR 5-YEAR GRID: 2004, 2009, 2014, 2019, 2024
   - All 48 jurisdictions covered for all years
   - Supports trend analysis (20-year window)

3. F7 Market cap/GDP (WDI):
   - ANNUAL but UNEVEN: some countries have 2024, others only 2017-2019
   - Main issue: Euronext/Nasdaq Nordic consolidation removes some countries

4. Savings/GDP (WDI):
   - ANNUAL, GOOD COVERAGE: ~198+ countries for 2024
   - Much less spotty than market cap data

5. Listed companies (WDI):
   - ANNUAL but same gaps as market cap

ALIGNMENT OPTIONS:
- Option A: Use 2019 as anchor year (matches Doing Business; WGI has 2019; WDI has ~2019)
- Option B: Use latest available (maximize data freshness, accept 1-3 year spread)
- Option C: Dual table — 2019 snapshot + latest snapshot
""")
