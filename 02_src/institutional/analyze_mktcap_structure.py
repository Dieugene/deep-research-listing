"""
Анализ структуры F7 MktCap/GDP: выявление «hub»-юрисдикций,
где капитализация раздута за счёт экстерриториальных листингов.

Сопоставление cap/GDP с числом листингованных компаний и размером экономики.
"""
import logging
import os
import sys

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")

os.makedirs(FIGURES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

df = pd.read_csv(os.path.join(DATA_DIR, "master_factors.csv"), index_col="country")

# ── Core data ────────────────────────────────────────────────────────
cap_gdp = df["F7_mktcap_gdp_val"]
listed_n = df["F7x_listed_n_val"]
cap_usd = df["F7x_mktcap_usd_val"]
legal = df["F1_legal_origin"]
mkt_group = df["market_group"]

# =====================================================================
# 1. Ranking by cap/GDP
# =====================================================================
log.info("=" * 75)
log.info("MktCap/GDP RANKING")
log.info("=" * 75)

ranked = df[["F7_mktcap_gdp_val", "F7x_listed_n_val", "F7x_mktcap_usd_val",
             "market_group", "F1_legal_origin"]].dropna(subset=["F7_mktcap_gdp_val"])
ranked = ranked.sort_values("F7_mktcap_gdp_val", ascending=False)

for c in ranked.index:
    cap = ranked.loc[c, "F7_mktcap_gdp_val"]
    n = ranked.loc[c, "F7x_listed_n_val"]
    usd = ranked.loc[c, "F7x_mktcap_usd_val"]
    mg = ranked.loc[c, "market_group"]
    n_str = f"{int(n):>6d}" if pd.notna(n) else "   N/A"
    usd_str = f"{usd/1e9:>8.0f}B" if pd.notna(usd) else "     N/A"
    flag = ""
    if cap > 200:
        flag = " <<< EXTREME"
    elif cap > 100:
        flag = " << HIGH"
    log.info(f"  {c:28s} | cap/GDP={cap:>7.1f}% | listed={n_str} | "
             f"cap={usd_str} | {mg}{flag}")

# =====================================================================
# 2. Natural breaks analysis
# =====================================================================
log.info("")
log.info("=" * 75)
log.info("DISTRIBUTION BREAKS")
log.info("=" * 75)

vals = ranked["F7_mktcap_gdp_val"].values
log.info(f"  N = {len(vals)}")
log.info(f"  Min = {vals.min():.1f}%  Max = {vals.max():.1f}%")
log.info(f"  Median = {np.median(vals):.1f}%")
log.info(f"  Mean = {np.mean(vals):.1f}%")
log.info(f"  P75 = {np.percentile(vals, 75):.1f}%")
log.info(f"  P90 = {np.percentile(vals, 90):.1f}%")
log.info(f"  P95 = {np.percentile(vals, 95):.1f}%")

# Potential thresholds for "hub" classification
thresholds = [100, 150, 200]
for t in thresholds:
    above = ranked[ranked["F7_mktcap_gdp_val"] > t].index.tolist()
    log.info(f"  >={t}%: {len(above)} jurisdictions: {above}")

# =====================================================================
# 3. Log transform assessment
# =====================================================================
log.info("")
log.info("=" * 75)
log.info("LOG TRANSFORM ASSESSMENT")
log.info("=" * 75)

raw_skew = pd.Series(vals).skew()
log_vals = np.log1p(vals)
log_skew = pd.Series(log_vals).skew()
log.info(f"  Raw skewness:    {raw_skew:+.3f}")
log.info(f"  Log1p skewness:  {log_skew:+.3f}")
log.info(f"  Log transform {'HELPS' if abs(log_skew) < abs(raw_skew) else 'does not help'}")

# After log, check if HK is still an outlier
log_series = pd.Series(log_vals, index=ranked.index)
q1, q3 = log_series.quantile(0.25), log_series.quantile(0.75)
iqr = q3 - q1
outliers = log_series[log_series > q3 + 1.5 * iqr]
log.info(f"\n  After log transform, outliers (IQR method):")
if outliers.empty:
    log.info(f"    None")
else:
    for c in outliers.index:
        log.info(f"    {c}: log1p={outliers[c]:.2f} (original={cap_gdp[c]:.1f}%)")

# =====================================================================
# 4. Scatter: cap/GDP vs listed companies
# =====================================================================
both = df[["F7_mktcap_gdp_val", "F7x_listed_n_val", "market_group"]].dropna()

fig, axes = plt.subplots(1, 2, figsize=(18, 8))

# Raw
ax = axes[0]
colors = {"DM": "steelblue", "EM": "orange"}
for mg_val in ["DM", "EM"]:
    sub = both[both["market_group"] == mg_val]
    ax.scatter(sub["F7x_listed_n_val"], sub["F7_mktcap_gdp_val"],
               c=colors[mg_val], label=mg_val, s=60, edgecolors="black", linewidth=0.5)

for c in both.index:
    cap = both.loc[c, "F7_mktcap_gdp_val"]
    n = both.loc[c, "F7x_listed_n_val"]
    if cap > 150 or n > 3000 or c == "Russia":
        ax.annotate(c, (n, cap), fontsize=7, alpha=0.8,
                    xytext=(5, 5), textcoords="offset points")
ax.set_xlabel("Listed companies (N)")
ax.set_ylabel("Market cap / GDP (%)")
ax.set_title("Raw: Cap/GDP vs Listed companies")
ax.legend()

# Log-log
ax = axes[1]
for mg_val in ["DM", "EM"]:
    sub = both[both["market_group"] == mg_val]
    ax.scatter(np.log1p(sub["F7x_listed_n_val"]), np.log1p(sub["F7_mktcap_gdp_val"]),
               c=colors[mg_val], label=mg_val, s=60, edgecolors="black", linewidth=0.5)

for c in both.index:
    cap = both.loc[c, "F7_mktcap_gdp_val"]
    n = both.loc[c, "F7x_listed_n_val"]
    if cap > 100 or n > 2000 or c in ("Russia", "Hong Kong", "Singapore", "Switzerland"):
        ax.annotate(c, (np.log1p(n), np.log1p(cap)), fontsize=7, alpha=0.8,
                    xytext=(5, 5), textcoords="offset points")
ax.set_xlabel("log(Listed companies)")
ax.set_ylabel("log(Market cap / GDP)")
ax.set_title("Log-scale: Cap/GDP vs Listed companies")
ax.legend()

plt.suptitle("Market structure: identifying financial hub jurisdictions", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "mktcap_structure.png"), dpi=150)
log.info(f"\n  Saved: mktcap_structure.png")

# =====================================================================
# 5. "Hub" characteristic: cap/GDP per listed company
# =====================================================================
log.info("")
log.info("=" * 75)
log.info("CAP-PER-LISTED-COMPANY (proxy for avg company size relative to GDP)")
log.info("=" * 75)

both2 = df[["F7_mktcap_gdp_val", "F7x_listed_n_val"]].dropna().copy()
both2["cap_per_company"] = both2["F7_mktcap_gdp_val"] / both2["F7x_listed_n_val"]
both2 = both2.sort_values("cap_per_company", ascending=False)

log.info("  Top 15 by cap/GDP per listed company:")
for c in both2.head(15).index:
    cpg = both2.loc[c, "F7_mktcap_gdp_val"]
    n = both2.loc[c, "F7x_listed_n_val"]
    ratio = both2.loc[c, "cap_per_company"]
    log.info(f"    {c:28s} | cap/GDP={cpg:>7.1f}% | N={int(n):>5d} | "
             f"ratio={ratio:.2f}%/co")

plt.close("all")
