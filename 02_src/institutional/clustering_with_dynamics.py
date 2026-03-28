"""
Кластеризация: вариант A (статика) vs вариант B (с динамикой WGI).

Сравнение двух наборов признаков:
  A: F2a, F2b, F2c, WGI_composite, log(MktCap/GDP), log(Savings/GDP)
  B: A + WGI_composite_slope (OLS slope per decade, 2004-2024)

Выходные файлы:
  figures/clustering_A_dendrogram.png
  figures/clustering_B_dendrogram.png
  figures/clustering_AB_comparison.png
  figures/clustering_B_profiles.png
  figures/clustering_B_pca.png
  figures/clustering_B_tsne.png
  figures/wgi_trajectories.png
  cluster_assignments.csv (обновлён с обоими вариантами)
"""
import logging
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import seaborn as sns
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
from sklearn.metrics import silhouette_score

PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIGURES_DIR = os.path.join(DATA_DIR, "figures")
LOG_DIR = os.path.join(PROJECT_ROOT, "04_logs")

os.makedirs(FIGURES_DIR, exist_ok=True)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(os.path.join(LOG_DIR, "clustering_dynamics.log"),
                            encoding="utf-8"),
    ],
)
log = logging.getLogger(__name__)
sns.set_style("whitegrid")

CLUSTER_COLORS = {1: "#e74c3c", 2: "#3498db", 3: "#2ecc71", 4: "#f39c12",
                  5: "#9b59b6", 6: "#1abc9c", 7: "#e67e22", 8: "#34495e"}

# =====================================================================
# 0. LOAD & PREPARE
# =====================================================================
df = pd.read_csv(os.path.join(DATA_DIR, "master_factors.csv"), index_col="country")

df["WGI_composite"] = df[["F4_reg_quality_val", "F5_rule_of_law_val",
                           "F6_pol_stability_val"]].mean(axis=1)
df["F7_log_mktcap_gdp"] = np.log1p(df["F7_mktcap_gdp_val"])
df["Fx_log_savings_gdp"] = np.log1p(df["Fx_savings_gdp_val"])

FEATURES_A = [
    "F2a_disclosure_val", "F2b_director_liability_val",
    "F2c_shareholder_suits_val", "WGI_composite",
    "F7_log_mktcap_gdp", "Fx_log_savings_gdp",
]
LABELS_A = [
    "F2a Disclosure", "F2b Dir.Liab.", "F2c Shareh.Suits",
    "WGI Composite", "log(MktCap/GDP)", "log(Savings/GDP)",
]

FEATURES_B = FEATURES_A + ["WGI_composite_slope"]
LABELS_B = LABELS_A + ["WGI Trend (slope)"]

# Drop NaN for both sets
data_a = df[FEATURES_A].dropna().copy()
data_b = df[FEATURES_B].dropna().copy()

log.info(f"Variant A: {len(data_a)} jurisdictions, {len(FEATURES_A)} features")
log.info(f"Variant B: {len(data_b)} jurisdictions, {len(FEATURES_B)} features")
log.info(f"Dropped in A but not B: {set(data_a.index) - set(data_b.index)}")
log.info(f"Dropped in B but not A: {set(data_b.index) - set(data_a.index)}")

# Use common set for fair comparison
common_idx = sorted(set(data_a.index) & set(data_b.index))
log.info(f"Common jurisdictions: {len(common_idx)}")

data_a = data_a.loc[common_idx]
data_b = data_b.loc[common_idx]
countries = common_idx

scaler_a = StandardScaler()
X_a = scaler_a.fit_transform(data_a.values)

scaler_b = StandardScaler()
X_b = scaler_b.fit_transform(data_b.values)

legal_origin = df.loc[countries, "F1_legal_origin"]
market_group = df.loc[countries, "market_group"]
trajectory = df.loc[countries, "WGI_trajectory"] if "WGI_trajectory" in df.columns else None

# =====================================================================
# 1. WGI TRAJECTORIES VISUALIZATION
# =====================================================================
log.info("\n" + "=" * 70)
log.info("1. WGI TRAJECTORY VISUALIZATION")
log.info("=" * 70)

wgi_years = [2004, 2009, 2014, 2019, 2024]
fig, axes = plt.subplots(1, 3, figsize=(20, 7))

traj_colors = {
    "consistent_growth": "#2ecc71", "growth": "#82e0aa",
    "mixed_stable": "#aab7b8", "decline": "#f5b041",
    "consistent_decline": "#e74c3c",
}

for ax, (factor, label) in zip(axes, [
    ("F4_reg_quality", "F4 Regulatory Quality"),
    ("F5_rule_of_law", "F5 Rule of Law"),
    ("F6_pol_stability", "F6 Political Stability"),
]):
    for c in countries:
        vals = []
        for yr in wgi_years:
            cn = f"{factor}_{yr}"
            if cn in df.columns:
                vals.append(df.loc[c, cn])
            else:
                vals.append(np.nan)
        traj = df.loc[c, "WGI_trajectory"] if "WGI_trajectory" in df.columns else "mixed_stable"
        color = traj_colors.get(traj, "#aab7b8")
        alpha = 0.8 if c == "Russia" else 0.3
        lw = 2.5 if c == "Russia" else 0.8
        ax.plot(wgi_years, vals, color="red" if c == "Russia" else color,
                alpha=alpha, linewidth=lw,
                label=c if c == "Russia" else None)
    ax.set_title(label, fontsize=12)
    ax.set_xlabel("Year")
    ax.set_ylabel("Governance estimate")
    ax.grid(True, alpha=0.3)
    if ax == axes[0]:
        ax.legend(fontsize=9)

fig.suptitle("WGI trajectories 2004-2024 (Russia highlighted in red)", fontsize=14)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "wgi_trajectories.png"), dpi=150)
plt.close()
log.info("  Saved: wgi_trajectories.png")


# =====================================================================
# 2. CLUSTERING A (static, baseline)
# =====================================================================
log.info("\n" + "=" * 70)
log.info("2. CLUSTERING VARIANT A (static)")
log.info("=" * 70)

Z_a = linkage(X_a, method="ward", metric="euclidean")

sil_a = {}
for k in range(2, 11):
    labels = fcluster(Z_a, t=k, criterion="maxclust")
    sil_a[k] = silhouette_score(X_a, labels, metric="euclidean")
best_k_a = max(sil_a, key=sil_a.get)
log.info(f"  Best k (A): {best_k_a} (silhouette={sil_a[best_k_a]:.3f})")

labels_a = fcluster(Z_a, t=best_k_a, criterion="maxclust")

fig, ax = plt.subplots(figsize=(18, 9))
dendrogram(Z_a, labels=countries, leaf_rotation=90, leaf_font_size=8, ax=ax)
ax.set_title(f"Variant A (static, k={best_k_a}): Ward dendrogram", fontsize=14)
ax.set_ylabel("Distance")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "clustering_A_dendrogram.png"), dpi=150)
plt.close()
log.info("  Saved: clustering_A_dendrogram.png")


# =====================================================================
# 3. CLUSTERING B (with dynamics)
# =====================================================================
log.info("\n" + "=" * 70)
log.info("3. CLUSTERING VARIANT B (with WGI slope)")
log.info("=" * 70)

Z_b = linkage(X_b, method="ward", metric="euclidean")

sil_b = {}
for k in range(2, 11):
    labels = fcluster(Z_b, t=k, criterion="maxclust")
    sil_b[k] = silhouette_score(X_b, labels, metric="euclidean")
best_k_b = max(sil_b, key=sil_b.get)
log.info(f"  Best k (B): {best_k_b} (silhouette={sil_b[best_k_b]:.3f})")

labels_b = fcluster(Z_b, t=best_k_b, criterion="maxclust")

fig, ax = plt.subplots(figsize=(18, 9))
dendrogram(Z_b, labels=countries, leaf_rotation=90, leaf_font_size=8, ax=ax)
ax.set_title(f"Variant B (with WGI slope, k={best_k_b}): Ward dendrogram", fontsize=14)
ax.set_ylabel("Distance")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "clustering_B_dendrogram.png"), dpi=150)
plt.close()
log.info("  Saved: clustering_B_dendrogram.png")

# Silhouette comparison
log.info(f"\n  Silhouette scores comparison:")
log.info(f"  {'k':>3s} | {'A (static)':>10s} | {'B (+slope)':>10s} | {'diff':>6s}")
log.info("  " + "-" * 40)
for k in range(2, 11):
    diff = sil_b[k] - sil_a[k]
    log.info(f"  {k:3d} | {sil_a[k]:10.3f} | {sil_b[k]:10.3f} | {diff:+6.3f}")


# =====================================================================
# 4. COMPARISON A vs B
# =====================================================================
log.info("\n" + "=" * 70)
log.info("4. COMPARISON A vs B")
log.info("=" * 70)

# Cluster compositions
log.info(f"\nVariant A clusters (k={best_k_a}):")
for cl in sorted(set(labels_a)):
    members = [countries[i] for i in range(len(countries)) if labels_a[i] == cl]
    log.info(f"  A-{cl} ({len(members)}): {members}")

log.info(f"\nVariant B clusters (k={best_k_b}):")
for cl in sorted(set(labels_b)):
    members = [countries[i] for i in range(len(countries)) if labels_b[i] == cl]
    log.info(f"  B-{cl} ({len(members)}): {members}")

# Cross-tabulation A x B
ct = pd.crosstab(
    pd.Series(labels_a, index=countries, name="A"),
    pd.Series(labels_b, index=countries, name="B"),
)
log.info(f"\nCross-tabulation A x B:")
log.info("\n" + ct.to_string())

# Which countries changed cluster?
log.info("\nCountries that changed grouping:")
for i, c in enumerate(countries):
    a_cl = labels_a[i]
    b_cl = labels_b[i]
    # Find A-cluster mates that are NOT B-cluster mates
    a_mates = set(countries[j] for j in range(len(countries)) if labels_a[j] == a_cl)
    b_mates = set(countries[j] for j in range(len(countries)) if labels_b[j] == b_cl)
    lost = a_mates - b_mates - {c}
    gained = b_mates - a_mates - {c}
    if lost or gained:
        slope_val = df.loc[c, "WGI_composite_slope"] if "WGI_composite_slope" in df.columns else np.nan
        traj_val = df.loc[c, "WGI_trajectory"] if "WGI_trajectory" in df.columns else "?"
        log.info(f"  {c}: A-{a_cl} -> B-{b_cl} | slope={slope_val:+.3f} | traj={traj_val}")


# =====================================================================
# 5. VARIANT B PROFILES
# =====================================================================
log.info("\n" + "=" * 70)
log.info("5. VARIANT B PROFILES")
log.info("=" * 70)

X_b_df = pd.DataFrame(X_b, index=countries, columns=LABELS_B)
X_b_df["cluster"] = labels_b

profiles_b = X_b_df.groupby("cluster")[LABELS_B].mean()
log.info("\nStandardized profiles (B):")
log.info("\n" + profiles_b.round(2).to_string())

# Trajectory composition per cluster
if trajectory is not None:
    log.info("\nTrajectory composition per cluster (B):")
    for cl in sorted(set(labels_b)):
        members = [countries[i] for i in range(len(countries)) if labels_b[i] == cl]
        traj_counts = trajectory.loc[members].value_counts()
        lo_counts = legal_origin.loc[members].value_counts()
        log.info(f"  B-{cl}: traj={dict(traj_counts)} | legal={dict(lo_counts)}")

fig, ax = plt.subplots(figsize=(12, 5))
sns.heatmap(profiles_b, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            linewidths=0.5, ax=ax, cbar_kws={"label": "Std. deviations from mean"})
ax.set_title(f"Variant B cluster profiles (k={best_k_b}, with WGI slope)", fontsize=14)
ax.set_ylabel("Cluster")
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "clustering_B_profiles.png"), dpi=150)
plt.close()
log.info("  Saved: clustering_B_profiles.png")


# =====================================================================
# 6. VARIANT B: PCA + t-SNE
# =====================================================================
log.info("\n" + "=" * 70)
log.info("6. VARIANT B: PCA + t-SNE")
log.info("=" * 70)

pca = PCA(n_components=2)
X_pca_b = pca.fit_transform(X_b)
var_exp = pca.explained_variance_ratio_
log.info(f"  PCA: PC1={var_exp[0]*100:.1f}%, PC2={var_exp[1]*100:.1f}%, total={sum(var_exp)*100:.1f}%")

log.info(f"  PCA loadings (B):")
for i, label in enumerate(LABELS_B):
    log.info(f"    {label:25s} | PC1={pca.components_[0][i]:+.3f} | PC2={pca.components_[1][i]:+.3f}")

fig, axes = plt.subplots(1, 2, figsize=(22, 9))

# PCA
ax = axes[0]
for cl in sorted(set(labels_b)):
    mask = labels_b == cl
    ax.scatter(X_pca_b[mask, 0], X_pca_b[mask, 1],
               c=CLUSTER_COLORS.get(cl, "gray"), s=80,
               edgecolors="black", linewidth=0.5, label=f"Cluster {cl}")
for i, c in enumerate(countries):
    w = "bold" if c == "Russia" else "normal"
    col = "red" if c == "Russia" else "black"
    ax.annotate(c, (X_pca_b[i, 0], X_pca_b[i, 1]), fontsize=7,
                fontweight=w, color=col, alpha=0.85,
                xytext=(5, 5), textcoords="offset points")
ax.set_xlabel(f"PC1 ({var_exp[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({var_exp[1]*100:.1f}%)")
ax.set_title(f"PCA (Variant B, k={best_k_b})")
ax.legend(loc="upper right", fontsize=8)
ax.axhline(0, color="gray", linewidth=0.5, linestyle="--")
ax.axvline(0, color="gray", linewidth=0.5, linestyle="--")

# t-SNE
tsne = TSNE(n_components=2, perplexity=12, random_state=42,
             max_iter=2000, learning_rate="auto", init="pca")
X_tsne_b = tsne.fit_transform(X_b)

ax = axes[1]
for cl in sorted(set(labels_b)):
    mask = labels_b == cl
    ax.scatter(X_tsne_b[mask, 0], X_tsne_b[mask, 1],
               c=CLUSTER_COLORS.get(cl, "gray"), s=80,
               edgecolors="black", linewidth=0.5, label=f"Cluster {cl}")
for i, c in enumerate(countries):
    w = "bold" if c == "Russia" else "normal"
    col = "red" if c == "Russia" else "black"
    ax.annotate(c, (X_tsne_b[i, 0], X_tsne_b[i, 1]), fontsize=7,
                fontweight=w, color=col, alpha=0.85,
                xytext=(5, 5), textcoords="offset points")
ax.set_title(f"t-SNE (Variant B, perplexity=12)")
ax.legend(loc="upper right", fontsize=8)
ax.set_xticks([]); ax.set_yticks([])

fig.suptitle(f"Variant B: PCA and t-SNE projections (k={best_k_b})", fontsize=14)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "clustering_B_pca.png"), dpi=150)
plt.close()
log.info("  Saved: clustering_B_pca.png")


# =====================================================================
# 7. SIDE-BY-SIDE A vs B on same t-SNE
# =====================================================================
log.info("\n" + "=" * 70)
log.info("7. SIDE-BY-SIDE COMPARISON")
log.info("=" * 70)

# Use variant B's t-SNE embedding, color by A and B clusters
fig, axes = plt.subplots(1, 3, figsize=(24, 8))

# Panel 1: A clusters on t-SNE(B)
ax = axes[0]
for cl in sorted(set(labels_a)):
    mask = labels_a == cl
    ax.scatter(X_tsne_b[mask, 0], X_tsne_b[mask, 1],
               c=CLUSTER_COLORS.get(cl, "gray"), s=60,
               edgecolors="black", linewidth=0.3)
for i, c in enumerate(countries):
    ax.annotate(c, (X_tsne_b[i, 0], X_tsne_b[i, 1]), fontsize=5.5, alpha=0.7)
ax.set_title(f"Variant A (static, k={best_k_a})", fontsize=11)
ax.set_xticks([]); ax.set_yticks([])

# Panel 2: B clusters on t-SNE(B)
ax = axes[1]
for cl in sorted(set(labels_b)):
    mask = labels_b == cl
    ax.scatter(X_tsne_b[mask, 0], X_tsne_b[mask, 1],
               c=CLUSTER_COLORS.get(cl, "gray"), s=60,
               edgecolors="black", linewidth=0.3)
for i, c in enumerate(countries):
    ax.annotate(c, (X_tsne_b[i, 0], X_tsne_b[i, 1]), fontsize=5.5, alpha=0.7)
ax.set_title(f"Variant B (+ WGI slope, k={best_k_b})", fontsize=11)
ax.set_xticks([]); ax.set_yticks([])

# Panel 3: Trajectory coloring
ax = axes[2]
if trajectory is not None:
    for traj_type, color in traj_colors.items():
        mask = (trajectory.loc[countries] == traj_type).values
        if mask.any():
            ax.scatter(X_tsne_b[mask, 0], X_tsne_b[mask, 1],
                       c=color, s=60, edgecolors="black", linewidth=0.3,
                       label=traj_type.replace("_", " "))
for i, c in enumerate(countries):
    ax.annotate(c, (X_tsne_b[i, 0], X_tsne_b[i, 1]), fontsize=5.5, alpha=0.7)
ax.set_title("WGI trajectory type", fontsize=11)
ax.legend(fontsize=7, loc="upper right")
ax.set_xticks([]); ax.set_yticks([])

fig.suptitle("Comparison: A (static) vs B (+ dynamics) vs WGI trajectories", fontsize=13)
plt.tight_layout()
fig.savefig(os.path.join(FIGURES_DIR, "clustering_AB_comparison.png"), dpi=150)
plt.close()
log.info("  Saved: clustering_AB_comparison.png")


# =====================================================================
# 8. RUSSIA POSITION (variant B)
# =====================================================================
log.info("\n" + "=" * 70)
log.info("8. RUSSIA POSITION (Variant B)")
log.info("=" * 70)

if "Russia" in countries:
    ru_idx = countries.index("Russia")
    ru_cl_a = labels_a[ru_idx]
    ru_cl_b = labels_b[ru_idx]
    log.info(f"  Russia: A cluster={ru_cl_a}, B cluster={ru_cl_b}")

    # Nearest neighbors (B space)
    distances = np.sqrt(((X_b - X_b[ru_idx]) ** 2).sum(axis=1))
    dist_series = pd.Series(distances, index=countries).sort_values()
    log.info(f"\n  Nearest jurisdictions to Russia (Variant B):")
    for c in dist_series.index[1:11]:
        d = dist_series[c]
        cl_b = labels_b[countries.index(c)]
        lo = legal_origin.loc[c]
        traj = trajectory.loc[c] if trajectory is not None else "?"
        slope = df.loc[c, "WGI_composite_slope"]
        log.info(f"    {c:25s} | dist={d:.3f} | B-{cl_b} | {lo} | slope={slope:+.3f} | {traj}")

    # Russia vs cluster mean (B)
    ru_vals = X_b_df.loc["Russia", LABELS_B]
    cl_mean = profiles_b.loc[ru_cl_b]
    log.info(f"\n  Russia vs B-{ru_cl_b} mean (standardized):")
    for label in LABELS_B:
        rv = ru_vals[label]
        cm = cl_mean[label]
        delta = rv - cm
        log.info(f"    {label:25s} | Russia={rv:+.2f} | Cluster={cm:+.2f} | delta={delta:+.2f}")


# =====================================================================
# 9. SAVE
# =====================================================================
result = pd.DataFrame(index=countries)
result["cluster_A"] = labels_a
result["cluster_B"] = labels_b
result["legal_origin"] = legal_origin.values
result["market_group"] = market_group.values
if trajectory is not None:
    result["WGI_trajectory"] = trajectory.values
result["WGI_composite_slope"] = df.loc[countries, "WGI_composite_slope"].values

for feat, label in zip(FEATURES_B, LABELS_B):
    result[label] = data_b[feat].values

out_path = os.path.join(DATA_DIR, "cluster_assignments.csv")
result.to_csv(out_path, encoding="utf-8", index_label="country")
log.info(f"\nSaved: {out_path}")
log.info("Done.")
