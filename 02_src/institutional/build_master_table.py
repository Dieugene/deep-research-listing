"""
Формирование master-таблицы институциональных факторов.

Каждый фактор хранится в двух колонках: value + year.
Это позволяет:
- видеть, за какой год значение
- оценить temporal spread
- принять решение о выравнивании per-factor, а не глобально

Выходной файл: 03_data/institutional/master_factors.csv
"""
import json
import logging
import os
import sys

import numpy as np
import pandas as pd

pd.set_option("future.no_silent_downcasting", True)

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
OUT_DIR = DATA_DIR
LOG_DIR = os.path.join(PROJECT_ROOT, "04_logs")

os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            os.path.join(LOG_DIR, "build_master_table.log"), encoding="utf-8"
        ),
    ],
)
log = logging.getLogger(__name__)

# ── Registry ─────────────────────────────────────────────────────────
REGISTRY_PATH = os.path.join(PROJECT_ROOT, "03_data", "jurisdictions_registry.json")
with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    JURISDICTIONS = {j["name_en"]: j for j in json.load(f)}
TARGET = sorted(JURISDICTIONS.keys())

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
    return int(col_name.split("[")[0].strip())


def latest_value_for_targets(df, yr_cols, country_col="Country Name"):
    """Extract latest available value per target country."""
    records = {}
    for _, row in df.iterrows():
        c = norm(row[country_col])
        if c is None or c not in JURISDICTIONS:
            continue
        if c in records:
            continue

        for yc in reversed(yr_cols):
            raw = row[yc]
            if str(raw).strip() in ("..", "") or pd.isna(raw):
                continue
            try:
                v = float(raw)
                records[c] = {"value": v, "year": extract_year(yc)}
                break
            except (ValueError, TypeError):
                continue

    return records


def value_for_fixed_year(df, yr_col, country_col="Country Name"):
    """Extract value from a specific year column."""
    records = {}
    for _, row in df.iterrows():
        c = norm(row[country_col])
        if c is None or c not in JURISDICTIONS:
            continue
        if c in records:
            continue

        raw = row[yr_col]
        if str(raw).strip() in ("..", "") or pd.isna(raw):
            continue
        try:
            records[c] = {"value": float(raw), "year": extract_year(yr_col)}
        except (ValueError, TypeError):
            pass

    return records


# =====================================================================
# Build master table
# =====================================================================
def build():
    master = pd.DataFrame(index=TARGET)
    master.index.name = "country"

    # Metadata
    for c in TARGET:
        meta = JURISDICTIONS[c]
        master.loc[c, "market_group"] = meta.get("market_group", "")
        master.loc[c, "eu_member"] = meta.get("eu_member", False)

    # ── F1: Legal Origin + ASDI (La Porta et al.) ──────────────────
    log.info("Loading F1: Legal Origins + ASDI")
    lp_path = os.path.join(DATA_DIR, "legal_origins_laporta.xlsx")
    lp = pd.read_excel(lp_path, sheet_name="Legal Origins")
    lp["country"] = lp["Country"].apply(norm)
    lp = lp.drop_duplicates(subset="country", keep="first")

    for _, row in lp.iterrows():
        c = row["country"]
        if c in JURISDICTIONS:
            master.loc[c, "F1_legal_origin"] = row["Legal Origin"]
            if pd.notna(row["ASDI"]):
                master.loc[c, "F1x_asdi_val"] = float(row["ASDI"])
                master.loc[c, "F1x_asdi_year"] = 2003

    n_origin = master["F1_legal_origin"].notna().sum()
    n_asdi = master["F1x_asdi_val"].notna().sum() if "F1x_asdi_val" in master.columns else 0
    log.info(f"  Legal origin: {n_origin}/48, ASDI: {n_asdi}/48")

    # ── F2: Doing Business (fixed 2019) ──────────────────────────────
    log.info("Loading F2: Protecting Minority Investors")
    f2_path = os.path.join(DATA_DIR, "F2 - Protecting Minority Investors.xlsx")
    f2 = pd.read_excel(f2_path, sheet_name="Sheet1")
    f2 = f2[f2["Location"].notna()].copy()
    f2["country"] = f2["Location"].apply(norm)
    f2 = f2.drop_duplicates(subset="country", keep="first")

    f2_cols = {
        "Extent of disclosure index (0-10)": "F2a_disclosure",
        "Extent of director liability index (0-10)": "F2b_director_liability",
        "Ease of shareholder suits index (0-10)": "F2c_shareholder_suits",
    }

    for src, dst in f2_cols.items():
        for _, row in f2.iterrows():
            c = row["country"]
            if c in JURISDICTIONS:
                try:
                    master.loc[c, f"{dst}_val"] = float(row[src])
                    master.loc[c, f"{dst}_year"] = 2019
                except (ValueError, TypeError):
                    pass

    # F2 composite
    for c in TARGET:
        vals = [master.loc[c, f"{dst}_val"] for dst in f2_cols.values()
                if pd.notna(master.loc[c, f"{dst}_val"])]
        if vals:
            master.loc[c, "F2_composite_val"] = np.mean(vals)
            master.loc[c, "F2_composite_year"] = 2019

    # ── F4-F6: WGI (all 5 time slices: 2004, 2009, 2014, 2019, 2024) ─
    log.info("Loading F4-F6: WGI (full time series)")
    wgi_path = os.path.join(DATA_DIR,
        "F4-6 P_Data_Extract_From_Worldwide_Governance_Indicators.xlsx")
    wgi = pd.read_excel(wgi_path, sheet_name="Data")
    wgi = wgi[wgi["Country Code"].notna()].copy()
    wgi["country"] = wgi["Country Name"].apply(norm)

    wgi_series = {
        "GOV_WGI_RQ.EST": "F4_reg_quality",
        "GOV_WGI_RL.EST": "F5_rule_of_law",
        "GOV_WGI_PV.EST": "F6_pol_stability",
    }
    wgi_yr_labels = [2004, 2009, 2014, 2019, 2024]
    wgi_yr_cols = [f"{y} [YR{y}]" for y in wgi_yr_labels]

    for code, factor in wgi_series.items():
        subset = wgi[wgi["Series Code"] == code]

        for yc, yr in zip(wgi_yr_cols, wgi_yr_labels):
            recs = value_for_fixed_year(subset, yc)
            col_name = f"{factor}_{yr}"
            if yr == 2024:
                col_name_val = f"{factor}_val"
                col_name_year = f"{factor}_year"
                for c, d in recs.items():
                    master.loc[c, col_name_val] = d["value"]
                    master.loc[c, col_name_year] = d["year"]
            for c, d in recs.items():
                master.loc[c, f"{factor}_{yr}"] = d["value"]

    # ── WGI dynamics: deltas, OLS slope, trajectory ────────────────
    log.info("Computing WGI dynamics (d_5y, d_10y, d_20y, slope, trajectory)")

    for factor in wgi_series.values():
        yr_col_names = [f"{factor}_{yr}" for yr in wgi_yr_labels]
        for c in TARGET:
            vals_by_year = {}
            for yr, cn in zip(wgi_yr_labels, yr_col_names):
                if cn in master.columns and pd.notna(master.loc[c, cn]):
                    vals_by_year[yr] = master.loc[c, cn]

            v24 = vals_by_year.get(2024)
            v19 = vals_by_year.get(2019)
            v14 = vals_by_year.get(2014)
            v04 = vals_by_year.get(2004)

            if v24 is not None and v19 is not None:
                master.loc[c, f"{factor}_delta_5y"] = v24 - v19
            if v24 is not None and v14 is not None:
                master.loc[c, f"{factor}_delta_10y"] = v24 - v14
            if v24 is not None and v04 is not None:
                master.loc[c, f"{factor}_delta_20y"] = v24 - v04

            # OLS slope (value per decade) using all available points
            if len(vals_by_year) >= 3:
                xs = np.array(list(vals_by_year.keys()), dtype=float)
                ys = np.array(list(vals_by_year.values()), dtype=float)
                xs_norm = (xs - xs.mean()) / 10.0  # per decade
                slope = np.polyfit(xs_norm, ys, 1)[0]
                master.loc[c, f"{factor}_slope"] = slope

    # ── WGI composite dynamics ─────────────────────────────────────
    for yr in wgi_yr_labels:
        comp_cols = [f"{f}_{yr}" for f in wgi_series.values()]
        existing = [cc for cc in comp_cols if cc in master.columns]
        if existing:
            master[f"WGI_composite_{yr}"] = master[existing].mean(axis=1)

    for c in TARGET:
        # Composite deltas
        for suffix, yr_from in [("5y", 2019), ("10y", 2014), ("20y", 2004)]:
            c24 = f"WGI_composite_2024"
            cfr = f"WGI_composite_{yr_from}"
            if c24 in master.columns and cfr in master.columns:
                v24 = master.loc[c, c24]
                vfr = master.loc[c, cfr]
                if pd.notna(v24) and pd.notna(vfr):
                    master.loc[c, f"WGI_composite_delta_{suffix}"] = v24 - vfr

        # Composite slope
        vals_by_year = {}
        for yr in wgi_yr_labels:
            cn = f"WGI_composite_{yr}"
            if cn in master.columns and pd.notna(master.loc[c, cn]):
                vals_by_year[yr] = master.loc[c, cn]
        if len(vals_by_year) >= 3:
            xs = np.array(list(vals_by_year.keys()), dtype=float)
            ys = np.array(list(vals_by_year.values()), dtype=float)
            xs_norm = (xs - xs.mean()) / 10.0
            slope = np.polyfit(xs_norm, ys, 1)[0]
            master.loc[c, "WGI_composite_slope"] = slope

    # Trajectory classification based on consecutive period changes
    for c in TARGET:
        comp_vals = []
        for yr in wgi_yr_labels:
            cn = f"WGI_composite_{yr}"
            if cn in master.columns and pd.notna(master.loc[c, cn]):
                comp_vals.append(master.loc[c, cn])
        if len(comp_vals) >= 3:
            diffs = [comp_vals[i+1] - comp_vals[i] for i in range(len(comp_vals)-1)]
            ups = sum(1 for d in diffs if d > 0.05)
            downs = sum(1 for d in diffs if d < -0.05)
            if ups >= 3:
                traj = "consistent_growth"
            elif downs >= 3:
                traj = "consistent_decline"
            elif ups >= 2 and downs == 0:
                traj = "growth"
            elif downs >= 2 and ups == 0:
                traj = "decline"
            else:
                traj = "mixed_stable"
            master.loc[c, "WGI_trajectory"] = traj

    log.info("  WGI trajectory distribution:")
    if "WGI_trajectory" in master.columns:
        for traj, cnt in master["WGI_trajectory"].value_counts().items():
            log.info(f"    {traj}: {cnt}")

    # ── F7: Market cap / GDP ─────────────────────────────────────────
    log.info("Loading F7+: WDI indicators")
    wdi_path = os.path.join(DATA_DIR,
        "F7 P_Data_Extract_From_World_Development_Indicators.xlsx")
    wdi = pd.read_excel(wdi_path, sheet_name="Data")
    wdi = wdi[wdi["Country Code"].notna()].copy()
    wdi["country"] = wdi["Country Name"].apply(norm)

    wdi_yr_cols = [c for c in wdi.columns if "[YR" in str(c)]

    wdi_factors = {
        "CM.MKT.LCAP.GD.ZS": "F7_mktcap_gdp",
        "CM.MKT.LCAP.CD":    "F7x_mktcap_usd",
        "CM.MKT.LDOM.NO":    "F7x_listed_n",
        "NY.GDS.TOTL.ZS":    "Fx_savings_gdp",
        "NY.GDS.TOTL.CD":    "Fx_savings_usd",
    }

    for series_code, factor in wdi_factors.items():
        subset = wdi[wdi["Series Code"] == series_code]
        recs = latest_value_for_targets(subset, wdi_yr_cols)
        for c, d in recs.items():
            master.loc[c, f"{factor}_val"] = d["value"]
            master.loc[c, f"{factor}_year"] = d["year"]

    # ── Data corrections ────────────────────────────────────────────
    # Qatar cap/GDP 2024: source has 0.0777 (decimal separator error);
    # prior year shows 78.94 -> corrected value is 77.71
    if "Qatar" in master.index and pd.notna(master.loc["Qatar", "F7_mktcap_gdp_val"]):
        raw = master.loc["Qatar", "F7_mktcap_gdp_val"]
        if raw < 1.0:
            corrected = raw * 1000
            log.info(f"  Qatar F7_mktcap_gdp corrected: {raw:.4f} -> {corrected:.2f} "
                     f"(decimal separator error in source)")
            master.loc["Qatar", "F7_mktcap_gdp_val"] = corrected

    # ── Summary stats ────────────────────────────────────────────────
    val_cols = [c for c in master.columns if c.endswith("_val")]
    year_cols = [c for c in master.columns if c.endswith("_year")]
    trend_cols = [c for c in master.columns if c.endswith("_delta_5y")]
    ref_cols = [c for c in master.columns if c.endswith("_2019")]

    log.info("")
    log.info("=" * 75)
    log.info("MASTER TABLE SUMMARY")
    log.info("=" * 75)
    log.info(f"Jurisdictions: {len(master)}")
    log.info(f"Value columns: {len(val_cols)}")
    log.info(f"Year columns: {len(year_cols)}")
    log.info(f"Trend columns: {len(trend_cols)}")
    log.info("")

    for vc in val_cols:
        n_ok = master[vc].notna().sum()
        factor_name = vc.replace("_val", "")
        yc = f"{factor_name}_year"
        if yc in master.columns:
            years = master[yc].dropna().unique()
            years_str = ", ".join(str(int(y)) for y in sorted(years))
        else:
            years_str = "N/A"
        log.info(f"  {factor_name:30s} | {n_ok:2d}/48 | years: {years_str}")

    # ── Temporal spread analysis for WDI factors ─────────────────────
    log.info("")
    log.info("TEMPORAL SPREAD ANALYSIS (WDI factors)")
    log.info("-" * 75)
    for series_code, factor in wdi_factors.items():
        yc = f"{factor}_year"
        if yc not in master.columns:
            continue
        years = master[yc].dropna()
        if years.empty:
            continue
        min_y, max_y = int(years.min()), int(years.max())
        spread = max_y - min_y
        median_y = int(years.median())
        log.info(f"  {factor:25s} | range: {min_y}-{max_y} | spread: {spread} yrs | median: {median_y}")

    # ── Missing data summary ─────────────────────────────────────────
    log.info("")
    log.info("MISSING DATA BY JURISDICTION")
    log.info("-" * 75)
    for c in TARGET:
        missing = []
        for vc in val_cols:
            if pd.isna(master.loc[c, vc]):
                missing.append(vc.replace("_val", ""))
        if missing:
            log.info(f"  {c:30s} | missing {len(missing)}: {missing}")
        else:
            log.info(f"  {c:30s} | COMPLETE")

    # ── Save ─────────────────────────────────────────────────────────
    out_path = os.path.join(OUT_DIR, "master_factors.csv")
    master.to_csv(out_path, encoding="utf-8")
    log.info(f"\nSaved: {out_path}")
    log.info(f"Shape: {master.shape}")

    return master


if __name__ == "__main__":
    master = build()
