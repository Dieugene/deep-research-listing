"""
Export institutional data as JSON files for the frontend.

Outputs:
  1. institutional_metrics.json  — per-jurisdiction metrics
  2. similar_jurisdictions.json  — nearest neighbours in MFA feature space
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd

# ── paths ──────────────────────────────────────────────────────────────
DATA_DIR = Path(__file__).resolve().parents[2] / "03_data" / "institutional"
MASTER   = DATA_DIR / "master_factors.csv"
STAGE4   = DATA_DIR / "stage4_cluster_assignments.csv"
STAGE4F  = DATA_DIR / "stage4_features.csv"

OUT_METRICS  = DATA_DIR / "institutional_metrics.json"
OUT_SIMILAR  = DATA_DIR / "similar_jurisdictions.json"

# ── ISO codes ──────────────────────────────────────────────────────────
ISO_MAP = {
    "Australia": "AU", "Austria": "AT", "Belgium": "BE", "Brazil": "BR",
    "Canada": "CA", "Chile": "CL", "China": "CN", "Colombia": "CO",
    "Czech Republic": "CZ", "Denmark": "DK", "Egypt": "EG", "Finland": "FI",
    "France": "FR", "Germany": "DE", "Greece": "GR", "Hong Kong": "HK",
    "Hungary": "HU", "India": "IN", "Indonesia": "ID", "Ireland": "IE",
    "Israel": "IL", "Italy": "IT", "Japan": "JP", "Kuwait": "KW",
    "Malaysia": "MY", "Mexico": "MX", "Netherlands": "NL", "New Zealand": "NZ",
    "Norway": "NO", "Peru": "PE", "Philippines": "PH", "Poland": "PL",
    "Portugal": "PT", "Qatar": "QA", "Russia": "RU", "Saudi Arabia": "SA",
    "Singapore": "SG", "South Africa": "ZA", "South Korea": "KR", "Spain": "ES",
    "Sweden": "SE", "Switzerland": "CH", "Taiwan": "TW", "Thailand": "TH",
    "Turkey": "TR", "United Arab Emirates": "AE", "United Kingdom": "GB",
    "United States": "US",
    # Russia split entities map to same ISO
    "Russia_1": "RU", "Russia_2": "RU",
    "Russia (2009-2021)": "RU", "Russia (2022-2024)": "RU",
}

CLUSTER_LABELS = {
    1: "English law, growing",
    2: "Deep markets, volatile",
    3: "Emerging, growing",
    4: "Mixed, declining",
    5: "Developed, stable",
}


def _safe(val):
    """Return None if value is NaN/missing, otherwise return the value."""
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return val


def _round(val, n=2):
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except (TypeError, ValueError):
        return val
    return round(float(val), n)


def _year(val):
    if val is None:
        return None
    try:
        if math.isnan(val):
            return None
    except (TypeError, ValueError):
        pass
    return int(val)


def percentile_of_score(values: np.ndarray, score: float) -> int:
    """Percentile rank of *score* within *values* (0-100, strict < method)."""
    valid = values[~np.isnan(values)]
    if len(valid) == 0:
        return 0
    below = np.sum(valid < score)
    equal = np.sum(valid == score)
    # mean of strict and weak percentile (same as scipy 'mean' kind)
    pct = ((below + 0.5 * equal) / len(valid)) * 100
    return int(round(pct))


# ── Output 1: institutional_metrics.json ───────────────────────────────
def build_metrics():
    df = pd.read_csv(MASTER)

    # Collect WGI value arrays for percentile computation
    rq_vals = df["F4_reg_quality_2024"].values
    rl_vals = df["F5_rule_of_law_2024"].values
    ps_vals = df["F6_pol_stability_2024"].values

    records = []
    for _, row in df.iterrows():
        country = row["country"]
        iso = ISO_MAP.get(country)
        if iso is None:
            print(f"  WARNING: no ISO code for '{country}', skipping")
            continue

        # WGI metrics
        rq = _safe(row.get("F4_reg_quality_2024"))
        rl = _safe(row.get("F5_rule_of_law_2024"))
        ps = _safe(row.get("F6_pol_stability_2024"))

        def wgi_metric(val, all_vals, year_col):
            if val is None:
                return None
            yr = _year(row.get(year_col)) if year_col else 2024
            return {
                "value": _round(val, 2),
                "year": yr if yr else 2024,
                "percentile": percentile_of_score(all_vals, val),
            }

        # WGI composite
        wgi_comp = _safe(row.get("WGI_composite_2024"))

        # Market cap & savings
        mktcap = _safe(row.get("F7_mktcap_gdp_val"))
        mktcap_yr = _year(row.get("F7_mktcap_gdp_year"))
        savings = _safe(row.get("Fx_savings_gdp_val"))
        savings_yr = _year(row.get("Fx_savings_gdp_year"))

        # Investor protection
        disc = _safe(row.get("F2a_disclosure_val"))
        dirl = _safe(row.get("F2b_director_liability_val"))
        shsuits = _safe(row.get("F2c_shareholder_suits_val"))
        comp = _safe(row.get("F2_composite_val"))
        ip_block = None
        if disc is not None or dirl is not None or shsuits is not None:
            ip_block = {
                "disclosure": {"value": int(disc), "max": 10} if disc is not None else None,
                "director_liability": {"value": int(dirl), "max": 10} if dirl is not None else None,
                "shareholder_suits": {"value": int(shsuits), "max": 10} if shsuits is not None else None,
                "composite": {"value": _round(comp, 1), "max": 10} if comp is not None else None,
                "source": "Doing Business 2020",
                "data_date": "2019-05-01",
            }

        # ASDI
        asdi_val = _safe(row.get("F1x_asdi_val"))
        asdi_yr = _year(row.get("F1x_asdi_year"))
        asdi_block = None
        if asdi_val is not None:
            asdi_block = {
                "value": _round(asdi_val, 2),
                "year": asdi_yr,
                "source": "Djankov et al. 2008",
            }

        rec = {
            "jurisdiction": country,
            "iso_code": iso,
            "market_group": row.get("market_group"),
            "legal_origin": row.get("F1_legal_origin"),
            "metrics": {
                "rule_of_law": wgi_metric(rl, rl_vals, "F5_rule_of_law_year"),
                "regulatory_quality": wgi_metric(rq, rq_vals, "F4_reg_quality_year"),
                "political_stability": wgi_metric(ps, ps_vals, "F6_pol_stability_year"),
                "wgi_composite": {
                    "value": _round(wgi_comp, 2),
                    "year": 2024,
                } if wgi_comp is not None else None,
                "market_cap_gdp_pct": {
                    "value": _round(mktcap, 1),
                    "year": mktcap_yr,
                } if mktcap is not None else None,
                "savings_gdp_pct": {
                    "value": _round(savings, 1),
                    "year": savings_yr,
                } if savings is not None else None,
                "investor_protection": ip_block,
                "asdi": asdi_block,
            },
        }
        records.append(rec)

    return records


# ── Output 2: similar_jurisdictions.json ───────────────────────────────
def build_similar():
    # Load stage4 cluster assignments (has entity, cluster_mfa, market_group, legal_origin, traj_slope, F2 sub-scores, log_mktcap)
    s4 = pd.read_csv(STAGE4).set_index("entity")

    # Load stage4 features for similarity (9 MFA features)
    feat = pd.read_csv(STAGE4F, index_col=0)

    entities = feat.index.tolist()

    # Z-score standardise features
    feat_arr = feat.values.astype(float)
    mu = feat_arr.mean(axis=0)
    sigma = feat_arr.std(axis=0, ddof=0)
    sigma[sigma == 0] = 1.0
    feat_z = (feat_arr - mu) / sigma

    # Compute pairwise Euclidean distances
    n = len(entities)
    dist_matrix = np.zeros((n, n))
    for i in range(n):
        for j in range(n):
            dist_matrix[i, j] = np.linalg.norm(feat_z[i] - feat_z[j])

    # Convert distances to similarity scores in intuitive 0-1 range.
    # Use: score = 1 - (d / d_max), where d_max is the maximum pairwise distance.
    # This gives 1.0 for identical objects and 0.0 for the most distant pair.
    d_max = dist_matrix.max()
    sim_matrix = 1.0 - (dist_matrix / d_max)

    # Precompute median log_mktcap for "deep_market" trait
    log_mktcap_median = s4["log_mktcap"].median()

    # Precompute F2 composite for "strong_investor_protection" trait
    s4["F2_composite"] = (s4["F2a"] + s4["F2b"] + s4["F2c"]) / 3.0

    def display_name(entity):
        if entity == "Russia_1":
            return "Russia (2009-2021)"
        if entity == "Russia_2":
            return "Russia (2022-2024)"
        return entity

    def iso_for(entity):
        return ISO_MAP.get(entity, ISO_MAP.get(display_name(entity)))

    def common_traits(e1, e2):
        r1, r2 = s4.loc[e1], s4.loc[e2]
        tags = []

        # Legal origin match
        lo1, lo2 = r1["legal_origin"], r2["legal_origin"]
        if lo1 == lo2:
            tag = lo1.lower().replace(" ", "_")
            if tag == "english":
                tags.append("common_law")
            else:
                tags.append(f"civil_law_{tag}")

        # Same market group
        mg1, mg2 = r1["market_group"], r2["market_group"]
        if mg1 == mg2:
            tags.append(mg1)

        # Same Stage IV cluster
        if r1["cluster_mfa"] == r2["cluster_mfa"]:
            tags.append("same_cluster")

        # WGI trajectory similarity (based on traj_slope)
        sl1, sl2 = r1["traj_slope"], r2["traj_slope"]
        if sl1 > 0.01 and sl2 > 0.01:
            tags.append("growing_wgi")
        elif abs(sl1) <= 0.01 and abs(sl2) <= 0.01:
            tags.append("stable_wgi")
        elif sl1 < -0.01 and sl2 < -0.01:
            tags.append("declining_wgi")

        # Deep market
        if r1["log_mktcap"] > log_mktcap_median and r2["log_mktcap"] > log_mktcap_median:
            tags.append("deep_market")

        # Strong investor protection
        if r1["F2_composite"] > 7 and r2["F2_composite"] > 7:
            tags.append("strong_investor_protection")

        return tags[:4]

    records = []
    for idx_i, entity in enumerate(entities):
        # Get top 5 neighbors (exclude self)
        sims = []
        for idx_j, other in enumerate(entities):
            if idx_i == idx_j:
                continue
            sims.append((other, sim_matrix[idx_i, idx_j]))

        sims.sort(key=lambda x: x[1], reverse=True)
        top5 = sims[:5]

        similar_list = []
        for other, score in top5:
            traits = common_traits(entity, other)
            similar_list.append({
                "iso_code": iso_for(other),
                "name_en": display_name(other),
                "score": _round(score, 2),
                "common_traits": traits,
            })

        cluster_id = int(s4.loc[entity, "cluster_mfa"])
        rec = {
            "jurisdiction": display_name(entity),
            "iso_code": iso_for(entity),
            "cluster": f"S4-{cluster_id}",
            "cluster_label": CLUSTER_LABELS.get(cluster_id, f"Cluster {cluster_id}"),
            "similar": similar_list,
        }
        records.append(rec)

    return records


# ── main ───────────────────────────────────────────────────────────────
def main():
    print("Building institutional_metrics.json ...")
    metrics = build_metrics()
    OUT_METRICS.write_text(json.dumps(metrics, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {len(metrics)} jurisdictions written to {OUT_METRICS}")

    print("\nBuilding similar_jurisdictions.json ...")
    similar = build_similar()
    OUT_SIMILAR.write_text(json.dumps(similar, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"  -> {len(similar)} entities written to {OUT_SIMILAR}")

    # ── verification ────────────────────────────────────────────────────
    print("\n=== VERIFICATION ===")

    # Sample entries
    for name in ["Australia", "Russia", "Hong Kong"]:
        matches = [m for m in metrics if m["jurisdiction"] == name]
        if matches:
            m = matches[0]
            print(f"\n--- {name} (metrics) ---")
            print(f"  iso_code: {m['iso_code']}, market_group: {m['market_group']}, legal_origin: {m['legal_origin']}")
            mx = m["metrics"]
            if mx.get("rule_of_law"):
                print(f"  rule_of_law: {mx['rule_of_law']}")
            if mx.get("regulatory_quality"):
                print(f"  regulatory_quality: {mx['regulatory_quality']}")
            if mx.get("market_cap_gdp_pct"):
                print(f"  market_cap_gdp_pct: {mx['market_cap_gdp_pct']}")
            if mx.get("investor_protection"):
                print(f"  investor_protection composite: {mx['investor_protection']['composite']}")
            if mx.get("asdi"):
                print(f"  asdi: {mx['asdi']}")
            else:
                print(f"  asdi: null")

    for name in ["Australia", "Russia (2009-2021)", "Russia (2022-2024)", "Hong Kong"]:
        matches = [s for s in similar if s["jurisdiction"] == name]
        if matches:
            s = matches[0]
            print(f"\n--- {name} (similar) ---")
            print(f"  cluster: {s['cluster']} ({s['cluster_label']})")
            for nb in s["similar"][:3]:
                print(f"  -> {nb['name_en']} ({nb['iso_code']}): score={nb['score']}, traits={nb['common_traits']}")

    # Missing data check
    print("\n--- Jurisdictions with missing WGI data ---")
    for m in metrics:
        mx = m["metrics"]
        missing = []
        if mx.get("rule_of_law") is None:
            missing.append("rule_of_law")
        if mx.get("regulatory_quality") is None:
            missing.append("reg_quality")
        if mx.get("political_stability") is None:
            missing.append("pol_stability")
        if mx.get("market_cap_gdp_pct") is None:
            missing.append("market_cap")
        if mx.get("asdi") is None:
            missing.append("asdi")
        if missing:
            print(f"  {m['jurisdiction']}: {', '.join(missing)}")


if __name__ == "__main__":
    main()
