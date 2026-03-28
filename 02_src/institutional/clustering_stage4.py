"""
Stage IV: Integrated MFA clustering.
Combines static profile (Blocks A, B) with dynamic trajectory (Block C)
using Multiple Factor Analysis for ~49 entities (48 jurisdictions with Russia split).
"""

import warnings
warnings.filterwarnings("ignore")

import numpy as np
import pandas as pd
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import seaborn as sns
from pathlib import Path
from sklearn.preprocessing import StandardScaler
from sklearn.decomposition import PCA
from sklearn.cluster import AgglomerativeClustering
from sklearn.metrics import silhouette_score, silhouette_samples
from sklearn.manifold import TSNE
from scipy.cluster.hierarchy import dendrogram, linkage, fcluster
from scipy.spatial.distance import cdist

# ── Paths ──────────────────────────────────────────────────────────────
DATA_DIR = Path("D:/_workspace/deep-research-listing/03_data/institutional")
FIG_DIR  = DATA_DIR / "figures"
FIG_DIR.mkdir(exist_ok=True)

MASTER  = DATA_DIR / "master_factors.csv"
TRAJ    = DATA_DIR / "final_features.csv"
STAGE1  = DATA_DIR / "cluster_assignments.csv"
STAGE3  = DATA_DIR / "final_cluster_assignments.csv"

# ── Colour palettes ───────────────────────────────────────────────────
LEGAL_ORIGIN_COLORS = {
    "English":      "#1b9e77",
    "French":       "#d95f02",
    "German":       "#7570b3",
    "Scandinavian": "#e7298a",
    "Socialist":    "#66a61e",
    "Mixed":        "#e6ab02",
}

def cluster_palette(k):
    """Colorblind-friendly palette for up to 12 clusters."""
    base = sns.color_palette("colorblind", max(k, 3))
    return {i + 1: base[i] for i in range(k)}


# ═══════════════════════════════════════════════════════════════════════
# 1. LOAD DATA
# ═══════════════════════════════════════════════════════════════════════
print("=" * 70)
print("STAGE IV — INTEGRATED MFA CLUSTERING")
print("=" * 70)

master = pd.read_csv(MASTER)
traj   = pd.read_csv(TRAJ, index_col=0)

print(f"\nmaster_factors : {master.shape[0]} rows")
print(f"final_features : {traj.shape[0]} rows  ({traj.shape[1]} trajectory features)")

# ═══════════════════════════════════════════════════════════════════════
# 2. BUILD ENTITY LIST  (Russia → Russia_1 + Russia_2)
# ═══════════════════════════════════════════════════════════════════════
# Static features from master
static_cols = {
    "F2a": "F2a_disclosure_val",
    "F2b": "F2b_director_liability_val",
    "F2c": "F2c_shareholder_suits_val",
    "F7":  "F7_mktcap_gdp_val",
    "Fx":  "Fx_savings_gdp_val",
}
meta_cols = {"legal_origin": "F1_legal_origin", "market_group": "market_group"}

static_df = master.set_index("country")[
    list(static_cols.values()) + list(meta_cols.values())
].copy()
static_df.columns = list(static_cols.keys()) + list(meta_cols.keys())

# Duplicate Russia row for Russia_1, Russia_2
russia_row = static_df.loc["Russia"].copy()
static_df.loc["Russia_1"] = russia_row
static_df.loc["Russia_2"] = russia_row
static_df.drop("Russia", inplace=True)

print(f"\nStatic entities (after Russia split): {len(static_df)}")

# Trajectory features — drop 'mean' (duplicates WGI_2024)
traj_cols_orig = traj.columns.tolist()
traj_no_mean = traj.drop(columns=["mean"])
traj_11 = traj_no_mean.columns.tolist()  # 11 features
print(f"Trajectory features (excl mean): {len(traj_11)}")

# Intersect entities
common = sorted(set(static_df.index) & set(traj_no_mean.index))
print(f"Common entities: {len(common)}")

static_df   = static_df.loc[common]
traj_no_mean = traj_no_mean.loc[common]

# ═══════════════════════════════════════════════════════════════════════
# 3. FEATURE ENGINEERING
# ═══════════════════════════════════════════════════════════════════════

# Block A: Investor Protection (F2a, F2b, F2c)
block_A = static_df[["F2a", "F2b", "F2c"]].astype(float).copy()

# Block B: Market Structure — log(1 + x)
block_B_raw = static_df[["F7", "Fx"]].astype(float).copy()
# Identify missing and impute with median
missing_F7 = block_B_raw["F7"].isna()
missing_Fx = block_B_raw["Fx"].isna()
imputed_entities = sorted(set(block_B_raw.index[missing_F7]) | set(block_B_raw.index[missing_Fx]))
if imputed_entities:
    print(f"\nImputed Block B (median) for: {imputed_entities}")
block_B_raw["F7"].fillna(block_B_raw["F7"].median(), inplace=True)
block_B_raw["Fx"].fillna(block_B_raw["Fx"].median(), inplace=True)

block_B = pd.DataFrame(index=block_B_raw.index)
block_B["log_mktcap"] = np.log1p(block_B_raw["F7"])
block_B["log_savings"] = np.log1p(block_B_raw["Fx"])

# Block C: Trajectory PCA (11 features → ≥85% variance)
scaler_C_raw = StandardScaler()
traj_scaled = pd.DataFrame(
    scaler_C_raw.fit_transform(traj_no_mean),
    index=traj_no_mean.index,
    columns=traj_11,
)

pca_traj = PCA()
pca_traj.fit(traj_scaled)
cumvar = np.cumsum(pca_traj.explained_variance_ratio_)
n_traj_pcs = int(np.searchsorted(cumvar, 0.85) + 1)
print(f"\nBlock C PCA: {n_traj_pcs} PCs explain {cumvar[n_traj_pcs-1]*100:.1f}% variance")
print(f"  Eigenvalues: {pca_traj.explained_variance_ratio_[:n_traj_pcs+2].round(4)}")

pca_traj_final = PCA(n_components=n_traj_pcs)
block_C = pd.DataFrame(
    pca_traj_final.fit_transform(traj_scaled),
    index=traj_scaled.index,
    columns=[f"TrajPC{i+1}" for i in range(n_traj_pcs)],
)

print(f"\nBlock dimensions: A={block_A.shape[1]}, B={block_B.shape[1]}, C={block_C.shape[1]}")

# ═══════════════════════════════════════════════════════════════════════
# 4. MFA  (manual implementation)
# ═══════════════════════════════════════════════════════════════════════

def manual_mfa(blocks, block_names):
    """
    Manual MFA:
    1. Standardize each block (z-score)
    2. PCA each block, divide by first singular value → equalize
    3. Concatenate
    4. Global PCA → MFA coordinates
    Returns: mfa_coords (DataFrame), block_info (dict)
    """
    normalized = []
    block_info = {}

    for name, blk in zip(block_names, blocks):
        sc = StandardScaler()
        Z = sc.fit_transform(blk.values)

        # PCA to get first singular value
        pca_blk = PCA()
        pca_blk.fit(Z)
        sv1 = np.sqrt(pca_blk.explained_variance_[0])  # first singular value

        Z_norm = Z / sv1
        normalized.append(Z_norm)

        block_info[name] = {
            "n_vars": blk.shape[1],
            "sv1": sv1,
            "var_explained_pct": pca_blk.explained_variance_ratio_[:3].tolist(),
            "columns": blk.columns.tolist(),
        }
        print(f"  Block {name}: {blk.shape[1]} vars, sv1={sv1:.4f}")

    # Concatenate
    X_concat = np.hstack(normalized)

    # Global PCA
    global_pca = PCA()
    coords = global_pca.fit_transform(X_concat)
    mfa_coords = pd.DataFrame(coords, index=blocks[0].index,
                               columns=[f"MFA{i+1}" for i in range(coords.shape[1])])

    block_info["global_pca"] = global_pca
    block_info["cumvar"] = np.cumsum(global_pca.explained_variance_ratio_)
    block_info["X_concat"] = X_concat

    return mfa_coords, block_info


print("\n--- MFA normalization ---")
blocks = [block_A, block_B, block_C]
block_names = ["A_InvestorProtection", "B_MarketStructure", "C_Trajectory"]
mfa_coords, mfa_info = manual_mfa(blocks, block_names)

print(f"\nMFA global variance explained (first 5): "
      f"{mfa_info['global_pca'].explained_variance_ratio_[:5].round(4)}")
print(f"Cumulative: {mfa_info['cumvar'][:5].round(4)}")


# ═══════════════════════════════════════════════════════════════════════
# 5. SIMPLE CONCATENATION  (Variant 1)
# ═══════════════════════════════════════════════════════════════════════
print("\n--- Simple concatenation (Variant 1) ---")
sc_A = StandardScaler(); Z_A = sc_A.fit_transform(block_A.values)
sc_B = StandardScaler(); Z_B = sc_B.fit_transform(block_B.values)
sc_C = StandardScaler(); Z_C = sc_C.fit_transform(block_C.values)
X_simple = np.hstack([Z_A, Z_B, Z_C])
simple_coords = pd.DataFrame(X_simple, index=block_A.index,
                              columns=(block_A.columns.tolist() +
                                       block_B.columns.tolist() +
                                       block_C.columns.tolist()))
print(f"Simple feature matrix: {X_simple.shape}")


# ═══════════════════════════════════════════════════════════════════════
# 6. CLUSTERING — SILHOUETTE SWEEP
# ═══════════════════════════════════════════════════════════════════════
K_RANGE = range(2, 13)

def ward_silhouettes(X, k_range):
    scores = {}
    for k in k_range:
        labels = AgglomerativeClustering(n_clusters=k, linkage="ward").fit_predict(X)
        scores[k] = silhouette_score(X, labels)
    return scores

sil_mfa    = ward_silhouettes(mfa_coords.values, K_RANGE)
sil_simple = ward_silhouettes(X_simple, K_RANGE)

best_k_mfa    = max(sil_mfa, key=sil_mfa.get)
best_k_simple = max(sil_simple, key=sil_simple.get)

# Also check 4-8 range
best_k_mfa_48    = max(range(4, 9), key=lambda k: sil_mfa[k])
best_k_simple_48 = max(range(4, 9), key=lambda k: sil_simple[k])

print(f"\n{'Method':<10} {'Best k (2-12)':<15} {'Silh':<8} {'Best k (4-8)':<15} {'Silh':<8}")
print("-" * 56)
print(f"{'MFA':<10} {best_k_mfa:<15} {sil_mfa[best_k_mfa]:<8.4f} "
      f"{best_k_mfa_48:<15} {sil_mfa[best_k_mfa_48]:<8.4f}")
print(f"{'Simple':<10} {best_k_simple:<15} {sil_simple[best_k_simple]:<8.4f} "
      f"{best_k_simple_48:<15} {sil_simple[best_k_simple_48]:<8.4f}")

# ── Choose k: always use 4-8 range for interpretability with 49 entities.
# k>8 yields clusters too small to interpret, and silhouettes are weak across the board.
chosen_k_mfa = best_k_mfa_48
chosen_k_simple = best_k_simple_48

print(f"\nChosen k (MFA):    {chosen_k_mfa}  (silh={sil_mfa[chosen_k_mfa]:.4f})")
print(f"Chosen k (Simple): {chosen_k_simple}  (silh={sil_simple[chosen_k_simple]:.4f})")

# ── Fit final clusters
Z_mfa_link    = linkage(mfa_coords.values, method="ward", metric="euclidean")
Z_simple_link = linkage(X_simple, method="ward", metric="euclidean")

labels_mfa    = fcluster(Z_mfa_link, t=chosen_k_mfa, criterion="maxclust")
labels_simple = fcluster(Z_simple_link, t=chosen_k_simple, criterion="maxclust")

sil_per_entity_mfa    = silhouette_samples(mfa_coords.values, labels_mfa)
sil_per_entity_simple = silhouette_samples(X_simple, labels_simple)


# ═══════════════════════════════════════════════════════════════════════
# 7. BUILD OUTPUT DATAFRAMES
# ═══════════════════════════════════════════════════════════════════════
entities = mfa_coords.index.tolist()

result = pd.DataFrame({
    "entity":           entities,
    "cluster_mfa":      labels_mfa,
    "cluster_simple":   labels_simple,
    "silhouette_mfa":   sil_per_entity_mfa.round(4),
    "silhouette_simple": sil_per_entity_simple.round(4),
    "legal_origin":     [static_df.loc[e, "legal_origin"] for e in entities],
    "market_group":     [static_df.loc[e, "market_group"] for e in entities],
    "F2a":              block_A["F2a"].values,
    "F2b":              block_A["F2b"].values,
    "F2c":              block_A["F2c"].values,
    "log_mktcap":       block_B["log_mktcap"].values,
    "log_savings":      block_B["log_savings"].values,
    "imputed_blockB":   [e in imputed_entities for e in entities],
})
# Add trajectory features
for col in traj_11:
    result[f"traj_{col}"] = traj_no_mean.loc[entities, col].values
# Add MFA coordinates (first 5)
n_mfa_show = min(5, mfa_coords.shape[1])
for i in range(n_mfa_show):
    result[f"MFA{i+1}"] = mfa_coords.iloc[:, i].values

result.to_csv(DATA_DIR / "stage4_cluster_assignments.csv", index=False)
print(f"\nSaved: stage4_cluster_assignments.csv  ({len(result)} entities)")

# Feature matrix with block labels
feat_matrix = pd.concat([block_A, block_B, block_C], axis=1)
feat_matrix.columns = (
    [f"A_{c}" for c in block_A.columns] +
    [f"B_{c}" for c in block_B.columns] +
    [f"C_{c}" for c in block_C.columns]
)
feat_matrix.to_csv(DATA_DIR / "stage4_features.csv")
print(f"Saved: stage4_features.csv  ({feat_matrix.shape})")


# ═══════════════════════════════════════════════════════════════════════
# 8. VISUALIZATIONS
# ═══════════════════════════════════════════════════════════════════════
DPI = 150

# Helper: mark Russia entities
def mark_russia(ax, xs, ys, entities_list, color="red", size=200):
    for e in ["Russia_1", "Russia_2"]:
        if e in entities_list:
            idx = entities_list.index(e)
            ax.scatter(xs[idx], ys[idx], marker="*", s=size, c=color,
                       edgecolors="black", linewidths=0.5, zorder=10)
            ax.annotate(e, (xs[idx], ys[idx]), fontsize=7, fontweight="bold",
                        color="red", xytext=(5, 5), textcoords="offset points")


# ── (a) Silhouette vs k ──────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(10, 5))
ks = list(K_RANGE)
ax.plot(ks, [sil_mfa[k] for k in ks], "o-", label="MFA", color="#1b9e77", lw=2)
ax.plot(ks, [sil_simple[k] for k in ks], "s--", label="Simple concat", color="#d95f02", lw=2)
ax.axvline(chosen_k_mfa, color="#1b9e77", ls=":", alpha=0.6, label=f"MFA chosen k={chosen_k_mfa}")
ax.axvline(chosen_k_simple, color="#d95f02", ls=":", alpha=0.6, label=f"Simple chosen k={chosen_k_simple}")
ax.set_xlabel("Number of clusters (k)")
ax.set_ylabel("Silhouette score")
ax.set_title("Stage IV: Silhouette vs k — MFA vs Simple Concatenation")
ax.legend()
ax.grid(alpha=0.3)
fig.tight_layout()
fig.savefig(FIG_DIR / "s4_silhouette_k.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_silhouette_k.png")


# ── (b) Dendrogram (MFA) ─────────────────────────────────────────────
fig, ax = plt.subplots(figsize=(16, 8))

# Color leaves by legal origin
lo_map = {e: static_df.loc[e, "legal_origin"] for e in entities}
leaf_colors = {}
for i, e in enumerate(entities):
    leaf_colors[i] = LEGAL_ORIGIN_COLORS.get(lo_map[e], "#999999")

def color_func(x):
    # x is an index into the original observations for leaves
    if x < len(entities):
        return leaf_colors.get(x, "#999999")
    return "#333333"

dend = dendrogram(
    Z_mfa_link,
    labels=np.array(entities),
    leaf_rotation=90,
    leaf_font_size=7,
    ax=ax,
    color_threshold=0,
    above_threshold_color="#333333",
)
# Color leaf labels by legal origin
xlbls = ax.get_xticklabels()
for lbl in xlbls:
    txt = lbl.get_text()
    lo = lo_map.get(txt, "")
    lbl.set_color(LEGAL_ORIGIN_COLORS.get(lo, "#333333"))
    if txt in ("Russia_1", "Russia_2"):
        lbl.set_fontweight("bold")
        lbl.set_color("red")

ax.set_title(f"Stage IV MFA Dendrogram (Ward, k={chosen_k_mfa})")
ax.set_ylabel("Distance")

# Legend for legal origins
handles = [mpatches.Patch(color=c, label=lo) for lo, c in LEGAL_ORIGIN_COLORS.items()
           if lo in set(lo_map.values())]
ax.legend(handles=handles, loc="upper right", fontsize=8)

fig.tight_layout()
fig.savefig(FIG_DIR / "s4_dendrogram.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_dendrogram.png")


# ── (c) PCA projection of MFA space ──────────────────────────────────
fig, ax = plt.subplots(figsize=(12, 8))
pal = cluster_palette(chosen_k_mfa)
x_pc = mfa_coords["MFA1"].values
y_pc = mfa_coords["MFA2"].values

for cl in sorted(set(labels_mfa)):
    mask = labels_mfa == cl
    ax.scatter(x_pc[mask], y_pc[mask], c=[pal[cl]], label=f"Cluster {cl}",
               s=60, edgecolors="white", linewidths=0.5, alpha=0.85)
    for i, m in enumerate(mask):
        if m:
            e = entities[i]
            if e not in ("Russia_1", "Russia_2"):
                ax.annotate(e, (x_pc[i], y_pc[i]), fontsize=5.5, alpha=0.75)

mark_russia(ax, x_pc, y_pc, entities)
var1 = mfa_info["global_pca"].explained_variance_ratio_[0] * 100
var2 = mfa_info["global_pca"].explained_variance_ratio_[1] * 100
ax.set_xlabel(f"MFA Dim 1 ({var1:.1f}%)")
ax.set_ylabel(f"MFA Dim 2 ({var2:.1f}%)")
ax.set_title(f"Stage IV: PCA of MFA Space (k={chosen_k_mfa})")
ax.legend(fontsize=8)
ax.grid(alpha=0.2)
fig.tight_layout()
fig.savefig(FIG_DIR / "s4_pca.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_pca.png")


# ── (d) Cluster profiles heatmap ─────────────────────────────────────
# Original features z-scores per cluster
profile_feats = ["F2a", "F2b", "F2c", "log_mktcap", "log_savings"]
# Add key trajectory features
key_traj = ["slope", "std", "frac_positive", "range", "residual_std"]
all_profile = profile_feats.copy()
for t in key_traj:
    all_profile.append(f"traj_{t}")

# Also add trajectory PCs
for i in range(block_C.shape[1]):
    all_profile.append(f"TrajPC{i+1}")
    result[f"TrajPC{i+1}"] = block_C.iloc[:, i].values

profile_df = result[["cluster_mfa"] + all_profile].copy()
# Z-score each feature
for col in all_profile:
    vals = profile_df[col].astype(float)
    profile_df[col] = (vals - vals.mean()) / (vals.std() + 1e-12)

cluster_means = profile_df.groupby("cluster_mfa")[all_profile].mean()

fig, ax = plt.subplots(figsize=(14, 6))
sns.heatmap(cluster_means.T, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
            ax=ax, linewidths=0.5)
ax.set_title(f"Stage IV: Cluster Profiles (mean z-scores, MFA k={chosen_k_mfa})")
ax.set_xlabel("Cluster")
ax.set_ylabel("Feature")
fig.tight_layout()
fig.savefig(FIG_DIR / "s4_profiles_heatmap.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_profiles_heatmap.png")


# ── (e) Russia neighbours ────────────────────────────────────────────
D_mfa = cdist(mfa_coords.values, mfa_coords.values, metric="euclidean")
dist_df = pd.DataFrame(D_mfa, index=entities, columns=entities)

fig, axes = plt.subplots(1, 2, figsize=(14, 6))
for idx_ax, ru in enumerate(["Russia_1", "Russia_2"]):
    ax = axes[idx_ax]
    dists = dist_df[ru].drop(ru).sort_values()
    top10 = dists.head(10)
    colors = ["#d95f02" if n.startswith("Russia") else "#1b9e77" for n in top10.index]
    ax.barh(range(len(top10)), top10.values, color=colors)
    ax.set_yticks(range(len(top10)))
    ax.set_yticklabels(top10.index, fontsize=8)
    ax.invert_yaxis()
    ax.set_xlabel("Euclidean distance (MFA space)")
    ax.set_title(f"{ru} — 10 nearest neighbours")
    ax.grid(alpha=0.3, axis="x")
fig.suptitle("Stage IV: Russia Nearest Neighbours in MFA Space", fontweight="bold")
fig.tight_layout()
fig.savefig(FIG_DIR / "s4_russia_neighbors.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_russia_neighbors.png")


# ── (f) t-SNE projection ─────────────────────────────────────────────
perp = min(15, len(entities) - 1)
tsne = TSNE(n_components=2, perplexity=perp, random_state=42, max_iter=2000)
coords_tsne = tsne.fit_transform(mfa_coords.values)

fig, ax = plt.subplots(figsize=(12, 8))
for cl in sorted(set(labels_mfa)):
    mask = labels_mfa == cl
    ax.scatter(coords_tsne[mask, 0], coords_tsne[mask, 1],
               c=[pal[cl]], label=f"Cluster {cl}", s=60,
               edgecolors="white", linewidths=0.5, alpha=0.85)
    for i, m in enumerate(mask):
        if m:
            e = entities[i]
            if e not in ("Russia_1", "Russia_2"):
                ax.annotate(e, (coords_tsne[i, 0], coords_tsne[i, 1]),
                            fontsize=5.5, alpha=0.7)

mark_russia(ax, coords_tsne[:, 0].tolist(), coords_tsne[:, 1].tolist(), entities)
ax.set_title(f"Stage IV: t-SNE of MFA Space (k={chosen_k_mfa})")
ax.legend(fontsize=8)
ax.grid(alpha=0.2)
fig.tight_layout()
fig.savefig(FIG_DIR / "s4_tsne.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_tsne.png")


# ── (g) Block contributions to MFA dimensions ────────────────────────
# Compute partial inertia: project each normalized block onto global axes
# and compute sum of squared coordinates per block per dimension
global_pca = mfa_info["global_pca"]
X_concat_norm = mfa_info["X_concat"]

# Split back into blocks
block_sizes = [block_A.shape[1], block_B.shape[1], block_C.shape[1]]
block_starts = [0] + list(np.cumsum(block_sizes[:-1]))

n_dims_show = min(5, mfa_coords.shape[1])
contributions = np.zeros((len(block_names), n_dims_show))

for b_idx, (bname, bstart, bsize) in enumerate(zip(block_names, block_starts, block_sizes)):
    block_data = X_concat_norm[:, bstart:bstart+bsize]
    # Project onto global components
    for d in range(n_dims_show):
        component = global_pca.components_[d]
        block_loadings = component[bstart:bstart+bsize]
        proj = block_data @ block_loadings
        contributions[b_idx, d] = np.var(proj) / global_pca.explained_variance_[d]

fig, ax = plt.subplots(figsize=(10, 5))
x_pos = np.arange(n_dims_show)
width = 0.25
colors_b = ["#1b9e77", "#d95f02", "#7570b3"]
for b_idx in range(len(block_names)):
    ax.bar(x_pos + b_idx * width, contributions[b_idx], width,
           label=block_names[b_idx], color=colors_b[b_idx])

ax.set_xticks(x_pos + width)
ax.set_xticklabels([f"Dim {i+1}\n({global_pca.explained_variance_ratio_[i]*100:.1f}%)"
                     for i in range(n_dims_show)], fontsize=9)
ax.set_ylabel("Block contribution (proportion of dim variance)")
ax.set_title("Stage IV: Block Contributions to MFA Dimensions")
ax.legend()
ax.grid(alpha=0.3, axis="y")
fig.tight_layout()
fig.savefig(FIG_DIR / "s4_mfa_block_contributions.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_mfa_block_contributions.png")


# ── (h) Stage comparison heatmap ──────────────────────────────────────
# Load previous stage results
stage1_df = pd.read_csv(STAGE1).set_index("country")
stage3_df = pd.read_csv(STAGE3).rename(columns={"entity": "ent"}).set_index("ent")

# Build comparison table
comp_rows = []
for e in entities:
    s1_label = None
    if e in stage1_df.index:
        s1_label = f"S1-{stage1_df.loc[e, 'cluster_A']}"
    elif e in ("Russia_1", "Russia_2") and "Russia" in stage1_df.index:
        s1_label = f"S1-{stage1_df.loc['Russia', 'cluster_A']}"

    s3_label = None
    if e in stage3_df.index:
        s3_label = f"S3-{stage3_df.loc[e, 'cluster']}"

    s4_label = f"S4-{result.loc[result['entity']==e, 'cluster_mfa'].values[0]}"

    comp_rows.append({
        "entity": e,
        "Stage_I": s1_label if s1_label else "n/a",
        "Stage_III": s3_label if s3_label else "n/a",
        "Stage_IV": s4_label,
    })

comp_df = pd.DataFrame(comp_rows).set_index("entity")

# Create numeric version for heatmap
# Map cluster labels to integers
def label_to_int(s):
    if s == "n/a":
        return -1
    return hash(s) % 100

comp_numeric = comp_df.copy()
# Assign unique integers per column
for col in ["Stage_I", "Stage_III", "Stage_IV"]:
    uniq = sorted(comp_df[col].unique())
    mapping = {v: i for i, v in enumerate(uniq)}
    comp_numeric[col] = comp_df[col].map(mapping)

fig, ax = plt.subplots(figsize=(8, 16))
sns.heatmap(comp_numeric.astype(float), annot=comp_df.values, fmt="",
            cmap="tab20", ax=ax, linewidths=0.3, cbar=False)
ax.set_title("Stage Comparison: Cluster Assignments across Stages I / III / IV")
ax.set_xlabel("")

# Highlight Russia
for i, e in enumerate(comp_df.index):
    if e in ("Russia_1", "Russia_2"):
        ax.get_yticklabels()[i].set_color("red")
        ax.get_yticklabels()[i].set_fontweight("bold")

fig.tight_layout()
fig.savefig(FIG_DIR / "s4_comparison_stages.png", dpi=DPI)
plt.close(fig)
print("  Saved: s4_comparison_stages.png")


# ═══════════════════════════════════════════════════════════════════════
# 9. COMPREHENSIVE RESULTS
# ═══════════════════════════════════════════════════════════════════════

print("\n" + "=" * 70)
print("RESULTS")
print("=" * 70)

# ── Cluster compositions (MFA)
print(f"\n{'-'*40}")
print(f"MFA CLUSTERING: k = {chosen_k_mfa}, silhouette = {sil_mfa[chosen_k_mfa]:.4f}")
print(f"{'-'*40}")

for cl in sorted(set(labels_mfa)):
    mask = result["cluster_mfa"] == cl
    members = result.loc[mask, "entity"].tolist()
    lo_dist = result.loc[mask, "legal_origin"].value_counts().to_dict()
    mg_dist = result.loc[mask, "market_group"].value_counts().to_dict()
    cl_sil = result.loc[mask, "silhouette_mfa"].mean()
    print(f"\n  Cluster {cl} (n={len(members)}, avg silh={cl_sil:.3f}):")
    print(f"    Legal origins: {lo_dist}")
    print(f"    Market groups: {mg_dist}")
    print(f"    Members: {', '.join(sorted(members))}")

# ── Cluster compositions (Simple)
print(f"\n{'-'*40}")
print(f"SIMPLE CONCATENATION: k = {chosen_k_simple}, silhouette = {sil_simple[chosen_k_simple]:.4f}")
print(f"{'-'*40}")

for cl in sorted(set(labels_simple)):
    mask = result["cluster_simple"] == cl
    members = result.loc[mask, "entity"].tolist()
    cl_sil = result.loc[mask, "silhouette_simple"].mean()
    print(f"\n  Cluster {cl} (n={len(members)}, avg silh={cl_sil:.3f}):")
    print(f"    Members: {', '.join(sorted(members))}")

# ── Russia analysis
print(f"\n{'-'*40}")
print("RUSSIA ANALYSIS")
print(f"{'-'*40}")

for ru in ["Russia_1", "Russia_2"]:
    cl_mfa = result.loc[result["entity"] == ru, "cluster_mfa"].values[0]
    cl_simple = result.loc[result["entity"] == ru, "cluster_simple"].values[0]
    sil_m = result.loc[result["entity"] == ru, "silhouette_mfa"].values[0]

    # Distance to centroid
    cl_mask = labels_mfa == cl_mfa
    centroid = mfa_coords.values[cl_mask].mean(axis=0)
    ru_idx = entities.index(ru)
    dist_centroid = np.linalg.norm(mfa_coords.values[ru_idx] - centroid)

    # Nearest neighbours
    dists_ru = dist_df[ru].drop(ru).sort_values()
    top5 = dists_ru.head(5)

    print(f"\n  {ru}:")
    print(f"    MFA cluster: {cl_mfa}  |  Simple cluster: {cl_simple}  |  Silh (MFA): {sil_m:.4f}")
    print(f"    Distance to MFA cluster centroid: {dist_centroid:.4f}")
    print(f"    5 nearest neighbours: {list(zip(top5.index, top5.round(3).values))}")

# Distance between Russia_1 and Russia_2
r1_idx = entities.index("Russia_1")
r2_idx = entities.index("Russia_2")
r1r2_dist = D_mfa[r1_idx, r2_idx]
print(f"\n  Distance Russia_1 <-> Russia_2: {r1r2_dist:.4f}")
print(f"  Same MFA cluster: {labels_mfa[r1_idx] == labels_mfa[r2_idx]}")

# ── Silhouette per cluster
print(f"\n{'-'*40}")
print("SILHOUETTE ANALYSIS (MFA)")
print(f"{'-'*40}")
print(f"  Overall: {sil_mfa[chosen_k_mfa]:.4f}")
for cl in sorted(set(labels_mfa)):
    mask = labels_mfa == cl
    cl_sil = sil_per_entity_mfa[mask]
    print(f"  Cluster {cl}: mean={cl_sil.mean():.4f}, min={cl_sil.min():.4f}, max={cl_sil.max():.4f}, n={mask.sum()}")

# ── Block contributions
print(f"\n{'-'*40}")
print("BLOCK CONTRIBUTIONS TO MFA DIMENSIONS")
print(f"{'-'*40}")
print(f"  {'Block':<25} " + "  ".join(f"Dim{i+1}" for i in range(n_dims_show)))
for b_idx, bname in enumerate(block_names):
    vals = "  ".join(f"{contributions[b_idx, d]:.3f}" for d in range(n_dims_show))
    print(f"  {bname:<25} {vals}")

# ── Jurisdictions that changed clusters between stages
print(f"\n{'-'*40}")
print("STAGE TRANSITIONS")
print(f"{'-'*40}")

# Show the comparison table
print(comp_df.to_string())

# ── All silhouette scores
print(f"\n{'-'*40}")
print("SILHOUETTE SCORES BY K")
print(f"{'-'*40}")
print(f"  {'k':<5} {'MFA':<10} {'Simple':<10}")
for k in K_RANGE:
    print(f"  {k:<5} {sil_mfa[k]:<10.4f} {sil_simple[k]:<10.4f}")

# ── PCA loadings for trajectory Block C
print(f"\n{'-'*40}")
print(f"TRAJECTORY PCA LOADINGS (Block C, {n_traj_pcs} PCs)")
print(f"{'-'*40}")
loadings = pd.DataFrame(
    pca_traj_final.components_.T,
    index=traj_11,
    columns=[f"TrajPC{i+1}" for i in range(n_traj_pcs)],
)
print(loadings.round(3).to_string())

print(f"\n{'='*70}")
print("Stage IV complete. Output files:")
print(f"  {DATA_DIR / 'stage4_cluster_assignments.csv'}")
print(f"  {DATA_DIR / 'stage4_features.csv'}")
print(f"  Figures: {FIG_DIR / 's4_*.png'}")
print(f"{'='*70}")
