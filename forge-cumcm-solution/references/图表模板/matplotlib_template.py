"""复画 A175 表3；替换同结构 CSV 后可复用。"""
import argparse
import csv
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def render(csv_path, output_dir):
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        rows = sorted((float(r["mesh_step_m"]), float(r["power_kw_m2"]))
                      for r in csv.DictReader(handle))
    x, y = zip(*rows)
    output_dir.mkdir(parents=True, exist_ok=True)
    with plt.rc_context({"font.family": "DejaVu Sans", "font.size": 11,
                         "axes.spines.top": False, "axes.spines.right": False,
                         "svg.fonttype": "none"}):
        fig, ax = plt.subplots(figsize=(6.4, 4.2), layout="constrained")
        ax.plot(x, y, color="#276FBF", marker="o", linewidth=1.6, markersize=5)
        ax.set(xlabel="Mesh step (m)", ylabel="Power per mirror area (kW/m²)")
        ax.grid(axis="y", color="#E3E7EC", linewidth=0.7)
        ax.set_axisbelow(True)
        fig.suptitle("Mesh resolution sensitivity", fontsize=12)
        fig.text(0.5, -0.02, "Source: A175 (2023), PDF p.14, Table 3; transcribed values",
                 ha="center", fontsize=8, color="#555555")
        for suffix in ("png", "svg"):
            fig.savefig(output_dir / f"mesh_sensitivity.{suffix}", dpi=300,
                        bbox_inches="tight", facecolor="white")
        plt.close(fig)


if __name__ == "__main__":
    root = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data", type=Path, default=root / "a175_mesh.csv")
    parser.add_argument("--output", type=Path, default=root)
    args = parser.parse_args()
    render(args.data, args.output)
