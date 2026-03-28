"""
Verification & additional analysis for institutional clustering v3 report.

Parts:
  1. Verify key numbers from v2 report
  2. Additional sensitivity analyses (k=4, nearest neighbors, Gower distance)
  3. Generate new visualizations for v3 report

Output figures saved to 03_data/institutional/figures/ with prefix "v3_".
"""

import os
import sys
import warnings
import json

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.gridspec as gridspec
import seaborn as sns
from scipy.cluster.hierarchy import linkage, fcluster, dendrogram
from scipy.spatial.distance import pdist, squareform, euclidean
from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.decomposition import PCA

warnings.filterwarnings("ignore", category=FutureWarning)
sns.set_style("whitegrid")

# ── Paths ─────────────────────────────────────────────────────────────
PROJECT_ROOT = r"D:\_workspace\deep-research-listing"
DATA_DIR = os.path.join(PROJECT_ROOT, "03_data", "institutional")
FIG_DIR = os.path.join(DATA_DIR, "figures")
os.makedirs(FIG_DIR, exist_ok=True)

REGISTRY_PATH = os.path.join(PROJECT_ROOT, "03_data", "jurisdictions_registry.json")
with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
    JURISDICTIONS = {j["name_en"]: j for j in json.load(f)}

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
}

def norm(name):
    if pd.isna(name):
        return None
    s = str(name).strip().rstrip("*")
    return NAME_MAP.get(s, s)


# ── Tolerance helper ──────────────────────────────────────────────────
def check(name, actual, expected, tol=0.02, is_pct=False):
    diff = abs(actual - expected)
    ok = diff <= tol
    unit = "%" if is_pct else ""
    status = "OK" if ok else "MISMATCH"
    print(f"  [{status}] {name}: actual={actual:.6f}, expected={expected}, diff={diff:.6f}{unit}")
    return ok


# ======================================================================
# PART 1: VERIFY KEY NUMBERS
# ======================================================================
print("=" * 70)
print("PART 1: VERIFY KEY NUMBERS FROM v2 REPORT")
print("=" * 70)

# 1. Load master_factors
master = pd.read_csv(os.path.join(DATA_DIR, "master_factors.csv"), index_col="country")
print(f"\n[1] master_factors.csv loaded: {master.shape}")

# 2. WGI composite for Russia 2024
russia_wgi_2024 = master.loc["Russia", "WGI_composite_2024"]
print(f"\n[2] WGI composite Russia 2024:")
check("WGI_composite_2024", russia_wgi_2024, -1.04, tol=0.01)

# 3. Excluded jurisdictions (missing MktCap/GDP)
missing_mktcap = sorted(master[master["F7_mktcap_gdp_val"].isna()].index.tolist())
expected_excluded = ["Denmark", "Finland", "Italy", "Sweden", "Taiwan"]
match = missing_mktcap == expected_excluded
print(f"\n[3] Excluded jurisdictions (missing MktCap/GDP):")
print(f"  [{'OK' if match else 'MISMATCH'}] Found: {missing_mktcap}")
print(f"  Expected: {expected_excluded}")

# 4. Load final_cluster_assignments, verify Russia clusters
fca = pd.read_csv(os.path.join(DATA_DIR, "final_cluster_assignments.csv"))
fca = fca.set_index("entity")
r1_cluster = fca.loc["Russia_1", "cluster"]
r2_cluster = fca.loc["Russia_2", "cluster"]
print(f"\n[4] Russia cluster assignments:")
print(f"  [{'OK' if r1_cluster == 'F5' else 'MISMATCH'}] Russia_1: {r1_cluster} (expected F5)")
print(f"  [{'OK' if r2_cluster == 'F6' else 'MISMATCH'}] Russia_2: {r2_cluster} (expected F6)")

# 5. Silhouette scores
r1_sil = fca.loc["Russia_1", "silhouette"]
r2_sil = fca.loc["Russia_2", "silhouette"]
print(f"\n[5] Silhouette scores:")
check("Russia_1 silhouette", r1_sil, 0.329, tol=0.001)
check("Russia_2 silhouette", r2_sil, 0.247, tol=0.001)

# 6. Euclidean distance between Russia_1 and Russia_2 in 12D standardized space
final_features = pd.read_csv(os.path.join(DATA_DIR, "final_features.csv"), index_col=0)
scaler = StandardScaler()
X_std = scaler.fit_transform(final_features.values.astype(float))
X_df = pd.DataFrame(X_std, index=final_features.index, columns=final_features.columns)

r1_vec = X_df.loc["Russia_1"].values
r2_vec = X_df.loc["Russia_2"].values
dist_r1_r2 = euclidean(r1_vec, r2_vec)
print(f"\n[6] Euclidean distance Russia_1 <-> Russia_2 (12D standardized):")
check("Distance", dist_r1_r2, 6.693, tol=0.01)

# 7. Percentile of this distance among all pairwise distances
all_dists = pdist(X_std, metric="euclidean")
percentile = np.mean(all_dists <= dist_r1_r2) * 100
print(f"\n[7] Percentile of Russia_1-Russia_2 distance:")
print(f"  Distance {dist_r1_r2:.3f} is at the {percentile:.1f}th percentile")
check("Percentile", percentile, 84.0, tol=2.0)


# ======================================================================
# PART 2: ADDITIONAL ANALYSIS
# ======================================================================
print("\n" + "=" * 70)
print("PART 2: ADDITIONAL ANALYSIS FOR v3 REPORT")
print("=" * 70)

# Re-do clustering infrastructure
Z_final = linkage(X_std, method="ward")
entities = final_features.index.tolist()

# 8. Sensitivity: k=4 (statistical optimum)
print(f"\n[8] Sensitivity analysis: k=4 (statistical optimum)")
labels_k4 = fcluster(Z_final, 4, criterion="maxclust")
sil_k4 = silhouette_score(X_std, labels_k4)
print(f"  Silhouette at k=4: {sil_k4:.3f}")

for i, e in enumerate(entities):
    if "Russia" in e:
        print(f"  {e} -> cluster {labels_k4[i]}")

# Show cluster composition for k=4
for cl in sorted(set(labels_k4)):
    members = [entities[i] for i in range(len(entities)) if labels_k4[i] == cl]
    print(f"  Cluster {cl} ({len(members)}): {', '.join(sorted(members))}")

# Check if Russia_1 and Russia_2 are in same cluster at k=4
r1_idx = entities.index("Russia_1")
r2_idx = entities.index("Russia_2")
same_k4 = labels_k4[r1_idx] == labels_k4[r2_idx]
print(f"  Russia_1 and Russia_2 in same cluster at k=4: {same_k4}")

# 9. Russia's 5 nearest neighbors analysis
print(f"\n[9] Russia_1 nearest neighbors from F5 cluster (cluster 4 boundary test)")
# Get the k=6 labels (the ones used in the report)
labels_k6 = fcluster(Z_final, 6, criterion="maxclust")

# Map cluster labels to F-labels by matching Russia_1->F5, Russia_2->F6
r1_label_k6 = labels_k6[r1_idx]
r2_label_k6 = labels_k6[r2_idx]
print(f"  Russia_1 numeric label: {r1_label_k6}, Russia_2 numeric label: {r2_label_k6}")

# Distance from Russia_1 to all others
dists_from_r1 = np.array([euclidean(r1_vec, X_std[i]) for i in range(len(entities))])
neighbor_order = np.argsort(dists_from_r1)

print(f"  Russia_1's 10 nearest neighbors:")
for rank, idx in enumerate(neighbor_order[1:11], 1):
    cl_label = labels_k6[idx]
    print(f"    {rank}. {entities[idx]:20s} dist={dists_from_r1[idx]:.3f}  cluster={cl_label}")

# Specifically: nearest from cluster 4 (continental/DM cluster)
# First identify which numeric label is the "continental" cluster
# In k=6 solution, find the cluster that has many DM countries
# Load cluster_assignments for stage 1 info
ca_s1 = pd.read_csv(os.path.join(DATA_DIR, "cluster_assignments.csv"))

# For Russia_1, check average distance to each k=6 cluster
print(f"\n  Average distance from Russia_1 to each k=6 cluster centroid:")
for cl in sorted(set(labels_k6)):
    members_idx = [i for i in range(len(entities)) if labels_k6[i] == cl and entities[i] != "Russia_1"]
    if members_idx:
        centroid = X_std[members_idx].mean(axis=0)
        dist_to_centroid = euclidean(r1_vec, centroid)
        members = [entities[i] for i in members_idx]
        print(f"    Cluster {cl}: dist={dist_to_centroid:.3f} ({len(members)} members: {', '.join(sorted(members)[:5])}...)")

# 10. Gower distance with legal_origin
print(f"\n[10] Gower distance (manual) including legal_origin")

# Build a combined feature matrix: numeric features + legal_origin encoded
# Since gower package is not available, we compute it manually:
# Gower distance = weighted average of per-feature distances
# For numeric: |x_i - x_j| / range_i
# For categorical: 0 if same, 1 if different

# Get legal origin for each entity
tca = pd.read_csv(os.path.join(DATA_DIR, "trajectory_cluster_assignments.csv"))
tca = tca.set_index(tca.columns[0])
legal_map = tca["legal_origin"].to_dict()

# For Russia_1 and Russia_2, use Russia's legal origin
legal_for_entities = []
for e in entities:
    base = e.replace("_1", "").replace("_2", "")
    if base in legal_map:
        legal_for_entities.append(legal_map[base])
    else:
        legal_for_entities.append("Unknown")

print(f"  Legal origins: {set(legal_for_entities)}")

# Numeric features: normalize to [0,1] for Gower
feat_vals = final_features.values.astype(float)
feat_min = feat_vals.min(axis=0)
feat_range = feat_vals.max(axis=0) - feat_min
feat_range[feat_range == 0] = 1  # avoid division by zero
feat_norm = (feat_vals - feat_min) / feat_range

n_entities = len(entities)
n_numeric = feat_norm.shape[1]
n_features = n_numeric + 1  # +1 for legal_origin

# Compute Gower distance matrix
gower_matrix = np.zeros((n_entities, n_entities))
for i in range(n_entities):
    for j in range(i + 1, n_entities):
        # Numeric part
        num_dist = np.nanmean(np.abs(feat_norm[i] - feat_norm[j]))
        # Categorical part
        cat_dist = 0.0 if legal_for_entities[i] == legal_for_entities[j] else 1.0
        # Weighted average (equal weight)
        gower_d = (num_dist * n_numeric + cat_dist) / n_features
        gower_matrix[i, j] = gower_d
        gower_matrix[j, i] = gower_d

# Cluster with Gower distance
from scipy.cluster.hierarchy import linkage as linkage_sq
gower_condensed = squareform(gower_matrix)
Z_gower = linkage(gower_condensed, method="average")  # Ward requires Euclidean; use average for Gower

labels_gower_k6 = fcluster(Z_gower, 6, criterion="maxclust")
sil_gower = silhouette_score(gower_matrix, labels_gower_k6, metric="precomputed")
print(f"  Gower silhouette at k=6: {sil_gower:.3f}")

r1_gower_cl = labels_gower_k6[r1_idx]
r2_gower_cl = labels_gower_k6[r2_idx]
print(f"  Russia_1 Gower cluster: {r1_gower_cl}")
print(f"  Russia_2 Gower cluster: {r2_gower_cl}")
print(f"  Same cluster? {r1_gower_cl == r2_gower_cl}")

# Compare: are Russia_1 and Russia_2 in same cluster in Euclidean vs Gower?
same_eucl = labels_k6[r1_idx] == labels_k6[r2_idx]
same_gower = r1_gower_cl == r2_gower_cl
print(f"  Euclidean k=6: same cluster = {same_eucl}")
print(f"  Gower k=6:     same cluster = {same_gower}")

# Show Gower cluster members
for cl in sorted(set(labels_gower_k6)):
    members = [entities[i] for i in range(n_entities) if labels_gower_k6[i] == cl]
    has_russia = any("Russia" in m for m in members)
    marker = " <-- RUSSIA" if has_russia else ""
    print(f"  Gower cluster {cl} ({len(members)}){marker}: {', '.join(sorted(members))}")


# ======================================================================
# PART 3: VISUALIZATIONS
# ======================================================================
print("\n" + "=" * 70)
print("PART 3: GENERATE VISUALIZATIONS FOR v3 REPORT")
print("=" * 70)

# ── Helper: build Stage 1 data ────────────────────────────────────────
STAGE1_FEATURES = [
    "F2a_disclosure_val",
    "F2b_director_liability_val",
    "F2c_shareholder_suits_val",
    "WGI_composite",
    "F7_log_mktcap_gdp",
    "Fx_log_savings_gdp",
]
STAGE1_LABELS = [
    "F2a Disclosure",
    "F2b Dir. Liability",
    "F2c Shareholder Suits",
    "WGI Composite",
    "log(MktCap/GDP)",
    "log(Savings/GDP)",
]

master["WGI_composite"] = master[["F4_reg_quality_2024", "F5_rule_of_law_2024",
                                   "F6_pol_stability_2024"]].mean(axis=1)
master["F7_log_mktcap_gdp"] = np.log1p(master["F7_mktcap_gdp_val"])
master["Fx_log_savings_gdp"] = np.log1p(master["Fx_savings_gdp_val"])

s1_data = master[STAGE1_FEATURES].dropna()
s1_scaler = StandardScaler()
X_s1 = s1_scaler.fit_transform(s1_data.values)
X_s1_df = pd.DataFrame(X_s1, index=s1_data.index, columns=STAGE1_LABELS)

# Stage 1 clustering (Ward, k=7 as in report)
Z_s1 = linkage(X_s1, method="ward")
ca_s1_df = pd.read_csv(os.path.join(DATA_DIR, "cluster_assignments.csv"), index_col="country")
s1_labels = ca_s1_df.loc[s1_data.index, "cluster_A"].values


# ── Helper: build Stage 2 data ────────────────────────────────────────
STAGE2_FEATURES = STAGE1_FEATURES + ["WGI_composite_slope"]
STAGE2_LABELS = STAGE1_LABELS + ["WGI Trend (slope)"]

s2_data = master[STAGE2_FEATURES].dropna()
s2_scaler = StandardScaler()
X_s2 = s2_scaler.fit_transform(s2_data.values)
Z_s2 = linkage(X_s2, method="ward")
s2_labels = ca_s1_df.loc[s2_data.index, "cluster_B"].values

# ── 11. Radar chart: Russia profile vs cluster average vs sample average ──
print("\n[11] Generating v3_radar_russia.png")

russia_cluster = fca.loc["Russia_1", "cluster"]  # F5
# Use Stage 1 features for Russia
russia_s1_raw = s1_data.loc["Russia"]

# MinMax normalize all Stage 1 data to [0,1]
mm_scaler = MinMaxScaler()
s1_mm = pd.DataFrame(mm_scaler.fit_transform(s1_data), index=s1_data.index, columns=STAGE1_LABELS)

russia_profile = s1_mm.loc["Russia"]
sample_avg = s1_mm.mean()

# Russia's Stage 1 cluster
russia_s1_cluster = ca_s1_df.loc["Russia", "cluster_A"]
cluster_members = ca_s1_df[ca_s1_df["cluster_A"] == russia_s1_cluster].index
cluster_avg = s1_mm.loc[s1_mm.index.intersection(cluster_members)].mean()

# Radar plot
categories = STAGE1_LABELS
N = len(categories)
angles = np.linspace(0, 2 * np.pi, N, endpoint=False).tolist()
angles += angles[:1]  # close the polygon

fig, ax = plt.subplots(figsize=(8, 8), subplot_kw=dict(polar=True))

for profile, label, color, lw, alpha in [
    (cluster_avg, f"Cluster A-{russia_s1_cluster} avg", "#4CAF50", 2, 0.15),
    (sample_avg, "Full sample avg", "#9E9E9E", 1.5, 0.08),
    (russia_profile, "Russia", "#F44336", 2.5, 0.0),
]:
    values = profile.values.tolist() + [profile.values[0]]
    ax.plot(angles, values, "o-", color=color, linewidth=lw, label=label)
    if alpha > 0:
        ax.fill(angles, values, alpha=alpha, color=color)

ax.set_xticks(angles[:-1])
ax.set_xticklabels(categories, fontsize=9)
ax.set_ylim(0, 1)
ax.set_title("Russia profile vs cluster and sample averages\n(Stage 1 features, 0-1 normalized)",
             fontsize=12, pad=20)
ax.legend(loc="upper right", bbox_to_anchor=(1.3, 1.1), fontsize=9)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "v3_radar_russia.png"), dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: v3_radar_russia.png")


# ── 12. Parallel coordinates (Stage 1) ───────────────────────────────
print("\n[12] Generating v3_parallel_coordinates.png")

# Use standardized Stage 1 features, colored by cluster_A
fig, ax = plt.subplots(figsize=(14, 7))

# Assign colors by cluster
cluster_ids = sorted(ca_s1_df.loc[s1_data.index, "cluster_A"].unique())
cmap = plt.cm.get_cmap("tab10", len(cluster_ids))
cluster_colors = {cl: cmap(i) for i, cl in enumerate(cluster_ids)}

for country in s1_data.index:
    cl = ca_s1_df.loc[country, "cluster_A"]
    color = cluster_colors[cl]
    vals = X_s1_df.loc[country].values
    alpha = 0.3
    lw = 1
    if country == "Russia":
        color = "red"
        alpha = 1.0
        lw = 3
    ax.plot(range(len(STAGE1_LABELS)), vals, color=color, alpha=alpha, linewidth=lw)

# Add Russia label
russia_vals = X_s1_df.loc["Russia"].values
ax.annotate("Russia", xy=(len(STAGE1_LABELS) - 1, russia_vals[-1]),
            xytext=(10, 5), textcoords="offset points",
            fontsize=10, fontweight="bold", color="red")

ax.set_xticks(range(len(STAGE1_LABELS)))
ax.set_xticklabels(STAGE1_LABELS, fontsize=10, rotation=15, ha="right")
ax.set_ylabel("Standardized value (z-score)", fontsize=11)
ax.set_title("Parallel coordinates — 43 jurisdictions (Stage 1 features)\nColored by cluster, Russia in bold red",
             fontsize=12)

# Legend
from matplotlib.lines import Line2D
legend_elements = [Line2D([0], [0], color=cluster_colors[cl], lw=2, label=f"Cluster A-{cl}")
                   for cl in cluster_ids]
legend_elements.append(Line2D([0], [0], color="red", lw=3, label="Russia"))
ax.legend(handles=legend_elements, loc="upper left", fontsize=8, ncol=2)

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "v3_parallel_coordinates.png"), dpi=150)
plt.close()
print("  Saved: v3_parallel_coordinates.png")


# ── 13. Stage comparison panel ────────────────────────────────────────
print("\n[13] Generating v3_stage_comparison.png")

fig, axes = plt.subplots(1, 3, figsize=(18, 6))

# Stage 1 PCA
pca_s1 = PCA(n_components=2)
X_s1_pca = pca_s1.fit_transform(X_s1)
ax = axes[0]
for cl in cluster_ids:
    mask = ca_s1_df.loc[s1_data.index, "cluster_A"].values == cl
    ax.scatter(X_s1_pca[mask, 0], X_s1_pca[mask, 1], c=[cluster_colors[cl]],
               label=f"A-{cl}", alpha=0.6, s=40)
russia_idx_s1 = list(s1_data.index).index("Russia")
ax.scatter(X_s1_pca[russia_idx_s1, 0], X_s1_pca[russia_idx_s1, 1],
           c="red", s=150, marker="*", zorder=5, edgecolors="black")
ax.annotate("Russia", xy=(X_s1_pca[russia_idx_s1, 0], X_s1_pca[russia_idx_s1, 1]),
            xytext=(8, 8), textcoords="offset points", fontsize=9, fontweight="bold", color="red")
ax.set_xlabel(f"PC1 ({pca_s1.explained_variance_ratio_[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({pca_s1.explained_variance_ratio_[1]*100:.1f}%)")
ax.set_title("Stage 1: Static (43 jur., 6 features, k=7)")
ax.legend(fontsize=7, ncol=2)

# Stage 2 PCA
pca_s2 = PCA(n_components=2)
X_s2_pca = pca_s2.fit_transform(X_s2)
cluster_ids_s2 = sorted(ca_s1_df.loc[s2_data.index, "cluster_B"].unique())
cmap_s2 = plt.cm.get_cmap("tab10", len(cluster_ids_s2))
cluster_colors_s2 = {cl: cmap_s2(i) for i, cl in enumerate(cluster_ids_s2)}

ax = axes[1]
for cl in cluster_ids_s2:
    mask = ca_s1_df.loc[s2_data.index, "cluster_B"].values == cl
    ax.scatter(X_s2_pca[mask, 0], X_s2_pca[mask, 1], c=[cluster_colors_s2[cl]],
               label=f"B-{cl}", alpha=0.6, s=40)
russia_idx_s2 = list(s2_data.index).index("Russia")
ax.scatter(X_s2_pca[russia_idx_s2, 0], X_s2_pca[russia_idx_s2, 1],
           c="red", s=150, marker="*", zorder=5, edgecolors="black")
ax.annotate("Russia", xy=(X_s2_pca[russia_idx_s2, 0], X_s2_pca[russia_idx_s2, 1]),
            xytext=(8, 8), textcoords="offset points", fontsize=9, fontweight="bold", color="red")
ax.set_xlabel(f"PC1 ({pca_s2.explained_variance_ratio_[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({pca_s2.explained_variance_ratio_[1]*100:.1f}%)")
ax.set_title("Stage 2: +Dynamics (43 jur., 7 features, k=10)")
ax.legend(fontsize=6, ncol=3)

# Stage 3 PCA
pca_s3 = PCA(n_components=2)
X_s3_pca = pca_s3.fit_transform(X_std)
# Use k=6 labels
label_names_k6 = [f"F{labels_k6[i]}" for i in range(len(entities))]
unique_f = sorted(set(label_names_k6))
cmap_s3 = plt.cm.get_cmap("tab10", len(unique_f))
fcolors = {f: cmap_s3(i) for i, f in enumerate(unique_f)}

ax = axes[2]
for f in unique_f:
    mask = np.array(label_names_k6) == f
    ax.scatter(X_s3_pca[mask, 0], X_s3_pca[mask, 1], c=[fcolors[f]],
               label=f, alpha=0.6, s=40)

# Highlight Russia_1 and Russia_2
for rname, marker_char in [("Russia_1", "*"), ("Russia_2", "D")]:
    ridx = entities.index(rname)
    ax.scatter(X_s3_pca[ridx, 0], X_s3_pca[ridx, 1],
               c="red", s=150, marker=marker_char, zorder=5, edgecolors="black")
    ax.annotate(rname, xy=(X_s3_pca[ridx, 0], X_s3_pca[ridx, 1]),
                xytext=(8, 8), textcoords="offset points", fontsize=9, fontweight="bold", color="red")

ax.set_xlabel(f"PC1 ({pca_s3.explained_variance_ratio_[0]*100:.1f}%)")
ax.set_ylabel(f"PC2 ({pca_s3.explained_variance_ratio_[1]*100:.1f}%)")
ax.set_title("Stage 3: Trajectories (49 ent., 12 features, k=6)")
ax.legend(fontsize=7, ncol=2)

plt.suptitle("Russia's position across three clustering stages", fontsize=14, y=1.02)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "v3_stage_comparison.png"), dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: v3_stage_comparison.png")


# ── 14. Cluster stability: silhouette for k=2..10 across stages ──────
print("\n[14] Generating v3_cluster_stability.png")

fig, ax = plt.subplots(figsize=(10, 6))
ks = range(2, 11)

# Stage 1
sils_s1 = []
for k in ks:
    lab = fcluster(Z_s1, k, criterion="maxclust")
    sils_s1.append(silhouette_score(X_s1, lab))

# Stage 2
sils_s2 = []
for k in ks:
    lab = fcluster(Z_s2, k, criterion="maxclust")
    sils_s2.append(silhouette_score(X_s2, lab))

# Stage 3
sils_s3 = []
for k in ks:
    lab = fcluster(Z_final, k, criterion="maxclust")
    sils_s3.append(silhouette_score(X_std, lab))

width = 0.25
x = np.array(list(ks))
ax.bar(x - width, sils_s1, width, label="Stage 1 (static, 6 feat.)", color="#2196F3", alpha=0.8)
ax.bar(x, sils_s2, width, label="Stage 2 (+dynamics, 7 feat.)", color="#FF9800", alpha=0.8)
ax.bar(x + width, sils_s3, width, label="Stage 3 (trajectories, 12 feat.)", color="#4CAF50", alpha=0.8)

ax.set_xlabel("Number of clusters (k)", fontsize=11)
ax.set_ylabel("Silhouette score", fontsize=11)
ax.set_title("Cluster stability: silhouette scores across three stages", fontsize=13)
ax.set_xticks(list(ks))
ax.legend(fontsize=10)
ax.grid(axis="y", alpha=0.3)

# Annotate best k for each stage
best_s1 = list(ks)[np.argmax(sils_s1)]
best_s2 = list(ks)[np.argmax(sils_s2)]
best_s3 = list(ks)[np.argmax(sils_s3)]
ax.annotate(f"best={best_s1}", xy=(best_s1 - width, max(sils_s1)),
            xytext=(0, 8), textcoords="offset points", fontsize=8, ha="center", color="#1565C0")
ax.annotate(f"best={best_s2}", xy=(best_s2, max(sils_s2)),
            xytext=(0, 8), textcoords="offset points", fontsize=8, ha="center", color="#E65100")
ax.annotate(f"best={best_s3}", xy=(best_s3 + width, max(sils_s3)),
            xytext=(0, 8), textcoords="offset points", fontsize=8, ha="center", color="#2E7D32")

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "v3_cluster_stability.png"), dpi=150)
plt.close()
print("  Saved: v3_cluster_stability.png")
print(f"  Best k: Stage1={best_s1} ({max(sils_s1):.3f}), Stage2={best_s2} ({max(sils_s2):.3f}), Stage3={best_s3} ({max(sils_s3):.3f})")


# ── 15. Russia WGI trajectory annotated ──────────────────────────────
print("\n[15] Generating v3_russia_trajectory_annotated.png")

# Load trajectory panel
traj_panel = pd.read_csv(os.path.join(DATA_DIR, "trajectory_panel.csv"), index_col=0)
years = [int(c) for c in traj_panel.columns]

# Russia trajectory
russia_traj = traj_panel.loc["Russia"].values.astype(float)

# PELT breakpoint at 2022
bp_year = 2022
bp_idx = years.index(bp_year)

# Pre-break and post-break segments
pre_years = np.array(years[:bp_idx])
pre_vals = russia_traj[:bp_idx]
post_years = np.array(years[bp_idx:])
post_vals = russia_traj[bp_idx:]

# Fit slopes
pre_slope, pre_intercept = np.polyfit(pre_years, pre_vals, 1)
post_slope, post_intercept = np.polyfit(post_years, post_vals, 1)

fig, ax = plt.subplots(figsize=(12, 7))

# Russia main trajectory
ax.plot(years, russia_traj, "o-", color="red", linewidth=2.5, markersize=5, label="Russia", zorder=5)

# Slope lines
pre_fit = pre_slope * pre_years + pre_intercept
post_fit = post_slope * post_years + post_intercept
ax.plot(pre_years, pre_fit, "--", color="darkred", linewidth=1.5, alpha=0.7,
        label=f"Russia_1 slope: {pre_slope:.4f}/yr")
ax.plot(post_years, post_fit, "--", color="maroon", linewidth=1.5, alpha=0.7,
        label=f"Russia_2 slope: {post_slope:.4f}/yr")

# Breakpoint line
ax.axvline(bp_year, color="black", linestyle=":", linewidth=1.5, alpha=0.7)
ax.annotate("PELT breakpoint\n(2022)", xy=(bp_year, russia_traj[bp_idx]),
            xytext=(-60, 40), textcoords="offset points",
            fontsize=10, fontweight="bold",
            arrowprops=dict(arrowstyle="->", color="black", lw=1.5))

# Comparison trajectories: India, Turkey, Brazil
comparisons = {
    "India": ("#FF9800", "D"),
    "Turkey": ("#9C27B0", "s"),
    "Brazil": ("#2196F3", "^"),
}
for country, (color, marker) in comparisons.items():
    if country in traj_panel.index:
        vals = traj_panel.loc[country].values.astype(float)
        ax.plot(years, vals, f"{marker}-", color=color, linewidth=1.5, markersize=4,
                alpha=0.7, label=country)

# Shading for Russia_1 and Russia_2 periods
ax.axvspan(years[0], bp_year, alpha=0.05, color="blue", label="Russia_1 period")
ax.axvspan(bp_year, years[-1], alpha=0.05, color="red", label="Russia_2 period")

ax.set_xlabel("Year", fontsize=11)
ax.set_ylabel("WGI Composite (mean F4+F5+F6)", fontsize=11)
ax.set_title("Russia WGI trajectory with PELT breakpoint and comparison countries", fontsize=13)
ax.legend(loc="lower left", fontsize=9)
ax.grid(True, alpha=0.3)
ax.set_xticks(years)
ax.set_xticklabels(years, rotation=45, fontsize=8)

plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "v3_russia_trajectory_annotated.png"), dpi=150)
plt.close()
print("  Saved: v3_russia_trajectory_annotated.png")


# ── 16. Excluded jurisdictions analysis ──────────────────────────────
print("\n[16] Generating v3_excluded_jurisdictions.png")

excluded = ["Denmark", "Finland", "Italy", "Sweden", "Taiwan"]

# Features available for excluded: F2a, F2b, F2c, WGI_composite
avail_features = ["F2a_disclosure_val", "F2b_director_liability_val",
                   "F2c_shareholder_suits_val", "WGI_composite"]
avail_labels = ["F2a Disclosure", "F2b Dir. Liability", "F2c Shareh. Suits", "WGI Composite"]

# Get data for all 48 jurisdictions on these features
all_data = master[avail_features].copy()
all_data.columns = avail_labels

# Mark which are excluded vs included (in Stage 1 clusters)
all_data["group"] = "Included"
for ex in excluded:
    if ex in all_data.index:
        all_data.loc[ex, "group"] = "Excluded"

# Also add cluster info for included
for country in all_data.index:
    if country in ca_s1_df.index and all_data.loc[country, "group"] == "Included":
        all_data.loc[country, "cluster"] = f"A-{ca_s1_df.loc[country, 'cluster_A']}"
    else:
        all_data.loc[country, "cluster"] = "Excluded"

fig, axes = plt.subplots(2, 2, figsize=(14, 10))

for idx, (feat, label) in enumerate(zip(avail_labels, avail_labels)):
    ax = axes[idx // 2, idx % 2]

    # Box plot by cluster
    clusters_sorted = sorted([c for c in all_data["cluster"].unique() if c != "Excluded"])
    clusters_sorted.append("Excluded")

    data_for_plot = []
    labels_for_plot = []
    colors = []
    cmap_bp = plt.cm.get_cmap("tab10", len(clusters_sorted))

    for i, cl in enumerate(clusters_sorted):
        subset = all_data[all_data["cluster"] == cl][feat].dropna()
        data_for_plot.append(subset.values)
        labels_for_plot.append(cl)
        colors.append("salmon" if cl == "Excluded" else cmap_bp(i))

    bp = ax.boxplot(data_for_plot, labels=labels_for_plot, patch_artist=True, widths=0.6)
    for patch, color in zip(bp["boxes"], colors):
        patch.set_facecolor(color)
        patch.set_alpha(0.6)

    # Overlay excluded points with labels
    excl_data = all_data[(all_data["group"] == "Excluded") & all_data[feat].notna()]
    excl_x = clusters_sorted.index("Excluded") + 1
    for country in excl_data.index:
        val = excl_data.loc[country, feat]
        jitter = np.random.uniform(-0.15, 0.15)
        ax.plot(excl_x + jitter, val, "D", color="red", markersize=8, zorder=5)
        ax.annotate(country, xy=(excl_x + jitter, val),
                    xytext=(5, 3), textcoords="offset points", fontsize=7, color="red")

    ax.set_title(label, fontsize=11)
    ax.set_xticklabels(labels_for_plot, rotation=45, ha="right", fontsize=8)
    ax.grid(axis="y", alpha=0.3)

plt.suptitle("Excluded jurisdictions (missing MktCap/GDP) vs Stage 1 clusters\non available features",
             fontsize=13, y=1.01)
plt.tight_layout()
fig.savefig(os.path.join(FIG_DIR, "v3_excluded_jurisdictions.png"), dpi=150, bbox_inches="tight")
plt.close()
print("  Saved: v3_excluded_jurisdictions.png")

# Print summary of where excluded jurisdictions would likely fall
print("\n  Excluded jurisdiction profiles:")
for ex in excluded:
    if ex in master.index:
        vals = {l: master.loc[ex, f] for f, l in zip(avail_features, avail_labels)}
        print(f"    {ex}: {vals}")


print("\n" + "=" * 70)
print("VERIFICATION COMPLETE")
print("=" * 70)
