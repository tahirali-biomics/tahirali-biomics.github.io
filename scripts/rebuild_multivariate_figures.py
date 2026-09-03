from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
from matplotlib.patches import Ellipse
from sklearn.decomposition import PCA
from sklearn.discriminant_analysis import LinearDiscriminantAnalysis
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler


ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "workshops" / "multivariate_workshop_2_files" / "figure-html"
OUT.mkdir(parents=True, exist_ok=True)

NAVY = "#0D2238"
TEAL = "#14827A"
BLUE = "#1972BD"
SLATE = "#5D6F80"
GRID = "#DDE6ED"
COLORS = ["#145DA0", "#14827A", "#6A5AA8", "#D28A28", "#B74F6F"]


def make_data() -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray, list[str]]:
    rng = np.random.default_rng(123)
    labels = np.repeat(np.arange(5), 20)
    names = [f"Pop{i}" for i in range(1, 6)]
    lat = np.repeat(np.linspace(45, 49, 5), 20) + rng.normal(0, 0.1, 100)
    lon = np.repeat(np.linspace(8, 14, 5), 20) + rng.normal(0, 0.1, 100)
    temp = 8 + 0.9 * lat + rng.normal(0, 0.4, 100)
    prec = 800 - 50 * lat + rng.normal(0, 10, 100)
    elev = 100 * (lat - 44) + rng.normal(0, 20, 100)
    season = 5 + 0.4 * lon + rng.normal(0, 0.5, 100)
    climate = np.column_stack([temp, prec, elev, season])

    leaf_shift = np.linspace(-2, 2, 5)[labels]
    flower_shift = np.linspace(3, -3, 5)[labels]
    leaf = 20 + 0.6 * temp - 0.01 * prec + leaf_shift + rng.normal(0, 0.6, 100)
    flower = 100 - 2 * temp + 0.04 * season + flower_shift + rng.normal(0, 1.5, 100)
    height = 30 + 0.5 * temp - 0.03 * elev + leaf_shift + rng.normal(0, 1, 100)
    traits = np.column_stack([leaf, flower, height])

    genotype = np.empty((100, 50))
    for i, p in enumerate(np.linspace(0.1, 0.9, 5)):
        genotype[i * 20 : (i + 1) * 20] = rng.binomial(2, p, size=(20, 50))
    return labels, traits, genotype, climate, names


def base_ax(ax: plt.Axes, title: str, xlabel: str, ylabel: str) -> None:
    ax.set_facecolor("white")
    ax.set_title(title, loc="left", fontsize=14, color=NAVY, fontweight="bold", pad=12)
    ax.set_xlabel(xlabel, color=SLATE)
    ax.set_ylabel(ylabel, color=SLATE)
    ax.grid(color=GRID, linewidth=0.8)
    ax.set_axisbelow(True)
    ax.spines[["top", "right"]].set_visible(False)
    ax.spines[["left", "bottom"]].set_color("#BBC8D3")
    ax.tick_params(colors=SLATE)


def confidence_ellipse(x: np.ndarray, y: np.ndarray, ax: plt.Axes, color: str) -> None:
    covariance = np.cov(x, y)
    vals, vecs = np.linalg.eigh(covariance)
    order = vals.argsort()[::-1]
    vals, vecs = vals[order], vecs[:, order]
    angle = np.degrees(np.arctan2(*vecs[:, 0][::-1]))
    width, height = 2 * 1.8 * np.sqrt(np.maximum(vals, 1e-8))
    ax.add_patch(Ellipse((x.mean(), y.mean()), width, height, angle=angle, fill=False, color=color, linewidth=1.6, alpha=0.75))


def scatter_groups(ax: plt.Axes, xy: np.ndarray, labels: np.ndarray, names: list[str]) -> None:
    for i, name in enumerate(names):
        mask = labels == i
        ax.scatter(xy[mask, 0], xy[mask, 1], s=34, color=COLORS[i], label=name, edgecolor="white", linewidth=0.55, alpha=0.9)
        confidence_ellipse(xy[mask, 0], xy[mask, 1], ax, COLORS[i])
    ax.legend(frameon=False, ncol=5, loc="upper center", bbox_to_anchor=(0.5, -0.16), fontsize=8)


def save(fig: plt.Figure, name: str) -> None:
    fig.text(0.02, 0.015, "Reconstructed from the archived workshop's documented simulation design", color=SLATE, fontsize=8)
    fig.savefig(OUT / name, dpi=180, facecolor="#F7F9FC", bbox_inches="tight", pad_inches=0.18)
    plt.close(fig)


def pca_traits(labels: np.ndarray, traits: np.ndarray, names: list[str]) -> None:
    scaled = StandardScaler().fit_transform(traits)
    model = PCA(n_components=2).fit(scaled)
    xy = model.transform(scaled)
    fig, ax = plt.subplots(figsize=(8.4, 6.2), facecolor="#F7F9FC")
    base_ax(ax, "PCA of trait variation across populations", f"PC1 ({model.explained_variance_ratio_[0]:.1%})", f"PC2 ({model.explained_variance_ratio_[1]:.1%})")
    scatter_groups(ax, xy, labels, names)
    for loading, label in zip(model.components_.T, ["Leaf area", "Flowering time", "Height"]):
        end = loading * 1.15
        ax.annotate("", xy=(end[0], end[1]), xytext=(0, 0), arrowprops={"arrowstyle": "->", "color": NAVY, "lw": 1.5})
        ax.text(end[0] * 1.08, end[1] * 1.08, label, color=NAVY, fontsize=8.5, ha="center")
    save(fig, "unnamed-chunk-3-1.png")


def pcoa_genotypes(labels: np.ndarray, genotype: np.ndarray, names: list[str]) -> None:
    x = StandardScaler().fit_transform(genotype)
    distances = np.sqrt(((x[:, None, :] - x[None, :, :]) ** 2).sum(axis=2))
    n = len(distances)
    center = np.eye(n) - np.ones((n, n)) / n
    gram = -0.5 * center @ (distances**2) @ center
    eigenvalues, eigenvectors = np.linalg.eigh(gram)
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, eigenvectors = eigenvalues[order], eigenvectors[:, order]
    xy = eigenvectors[:, :2] * np.sqrt(np.maximum(eigenvalues[:2], 0))
    positive = eigenvalues[eigenvalues > 0].sum()
    fig, ax = plt.subplots(figsize=(8.4, 6.2), facecolor="#F7F9FC")
    base_ax(ax, "PCoA of genotype distances", f"PCoA1 ({eigenvalues[0]/positive:.1%})", f"PCoA2 ({eigenvalues[1]/positive:.1%})")
    scatter_groups(ax, xy, labels, names)
    save(fig, "unnamed-chunk-4-1.png")


def dapc_genotypes(labels: np.ndarray, genotype: np.ndarray, names: list[str]) -> None:
    x = StandardScaler().fit_transform(genotype)
    reduced = PCA(n_components=20).fit_transform(x)
    xy = LinearDiscriminantAnalysis(n_components=2).fit_transform(reduced, labels)
    fig, ax = plt.subplots(figsize=(8.4, 6.2), facecolor="#F7F9FC")
    base_ax(ax, "DAPC: discriminating predefined populations", "Discriminant function 1", "Discriminant function 2")
    scatter_groups(ax, xy, labels, names)
    save(fig, "unnamed-chunk-5-1.png")


def rda_plot(response: np.ndarray, climate: np.ndarray, labels: np.ndarray, names: list[str], title: str, output: str, response_names: list[str] | None = None) -> None:
    x = StandardScaler().fit_transform(climate)
    y = StandardScaler().fit_transform(response)
    fitted = LinearRegression().fit(x, y).predict(x)
    pca = PCA(n_components=2).fit(fitted)
    xy = pca.transform(fitted)
    fig, ax = plt.subplots(figsize=(8.4, 6.2), facecolor="#F7F9FC")
    base_ax(ax, title, f"RDA1 ({pca.explained_variance_ratio_[0]:.1%})", f"RDA2 ({pca.explained_variance_ratio_[1]:.1%})")
    scatter_groups(ax, xy, labels, names)
    for i, label in enumerate(["Temperature", "Precipitation", "Elevation", "Seasonality"]):
        corr = np.array([np.corrcoef(x[:, i], xy[:, j])[0, 1] for j in range(2)]) * 2.8
        ax.annotate("", xy=corr, xytext=(0, 0), arrowprops={"arrowstyle": "->", "color": NAVY, "lw": 1.5})
        ax.text(corr[0] * 1.08, corr[1] * 1.08, label, color=NAVY, fontsize=8, ha="center")
    if response_names is not None:
        for loading, label in zip(pca.components_.T, response_names):
            end = loading * 2.0
            ax.text(end[0], end[1], label, color=BLUE, fontsize=8.5, fontweight="bold", ha="center")
    save(fig, output)


def main() -> None:
    labels, traits, genotype, climate, names = make_data()
    pca_traits(labels, traits, names)
    pcoa_genotypes(labels, genotype, names)
    dapc_genotypes(labels, genotype, names)
    rda_plot(genotype, climate, labels, names, "RDA: genetic variation constrained by climate", "unnamed-chunk-6-1.png")
    rda_plot(traits, climate, labels, names, "RDA: trait variation constrained by climate", "unnamed-chunk-7-1.png", ["Leaf area", "Flowering time", "Height"])


if __name__ == "__main__":
    main()
