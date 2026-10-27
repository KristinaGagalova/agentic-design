"""Plot recorded RMSDs into a new results/<run-id>/comparison-<version> folder."""
import argparse
import csv
import json
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("campaign", type=Path)
    parser.add_argument("output", type=Path,
                        help="New results/<latest-run-id>/comparison-<version> directory; must not exist")
    args = parser.parse_args()
    entries = [json.loads(p.read_text()) for p in sorted((args.campaign / "entries").glob("*.json"))]
    requests, specs, runs, measured = {}, {}, {}, {}
    for entry in entries:
        data = entry.get("data", {})
        if entry["kind"] == "experiment_saved":
            exp = data["experiment"]
            specs[exp["id"]] = exp["spec"]
        if entry["kind"] == "tool_requested":
            requests[data["operation"]] = (entry["text"], data["arguments"])
        if entry["kind"] != "tool_result":
            continue
        operation, request = requests.get(data["operation"], (None, {}))
        result = data["result"]
        if operation == "submit_experiment":
            runs[result["run_id"]] = result["experiment_id"]
        if operation == "validate_motif":
            for row in result:
                measured[(request["run_id"], row["design"])] = row
    conditions = ["ubq-pilot-42"] + [
        f"ubq-screen-t{t}-ca{ca}-fr{fr}"
        for t in (50, 100) for ca, fr in ((1, 1), (0, 1), (1, 0), (0, 0))
    ]
    rows = []
    for (run, design), result in measured.items():
        exp = runs.get(run)
        if exp not in conditions:
            continue
        rows.append(dict(experiment=exp, run_id=run, design=design,
                         seed=int(design.rsplit("_", 1)[1]),
                         rmsd_A=result["motif_backbone_rmsd"]))
    fig, (ax, counts) = plt.subplots(2, 1, figsize=(14, 8), sharex=True,
                                    gridspec_kw={"height_ratios": [3, 1]})
    labels = []
    for x, exp in enumerate(conditions):
        group = sorted((r for r in rows if r["experiment"] == exp), key=lambda r: r["seed"])
        expected = specs[exp]["num_designs"]
        labels.append("Historical\nseeds 42–43" if x == 0 else exp.replace("ubq-screen-", "").replace("-", "\n"))
        for i, row in enumerate(group):
            offset = (i - (len(group) - 1) / 2) * 0.08
            ax.scatter(x + offset, row["rmsd_A"], color="tab:green" if row["rmsd_A"] < 1 else "tab:red")
            ax.annotate(str(row["seed"]), (x + offset, row["rmsd_A"]), xytext=(3, 6), textcoords="offset points", fontsize=8)
        passes = sum(r["rmsd_A"] < 1 for r in group)
        if group:
            counts.bar(x, passes, color="tab:green", width=0.6)
            counts.text(x, passes + 0.15, f"{passes}/{len(group)} measured\n{expected} planned", ha="center", fontsize=8)
        else:
            ax.text(x, 0.5, "Not measured", transform=ax.get_xaxis_transform(), rotation=90, ha="center", color="gray")
            counts.text(x, 0.2, "Not measured", ha="center", rotation=90, fontsize=8)
    ax.axhline(1, color="black", linestyle="--", label="Strict pass: RMSD < 1.0 Å")
    ax.set_ylabel("Recorded aligned motif backbone RMSD (Å)")
    ax.set_ylim(bottom=0)
    ax.legend(loc="upper right")
    ax.set_title("Ubiquitin A72–76 motif screen — recorded measurements only\nSeed labels; unmeasured outputs are neither passes nor geometry failures")
    counts.set_ylabel("Pass count")
    counts.set_ylim(0, 5.5)
    counts.set_xticks(range(len(labels)), labels)
    fig.text(0.5, 0.01, "80-residue scaffolds; not an A8-binding test. Generated backbones are not validated candidates.", ha="center", fontsize=9)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    args.output.mkdir(parents=False, exist_ok=False)
    with (args.output / "measurements.csv").open("x") as handle:
        writer = csv.DictWriter(handle, fieldnames=["experiment", "run_id", "design", "seed", "rmsd_A"])
        writer.writeheader()
        writer.writerows(rows)
    fig.savefig(args.output / "comparison.png", dpi=180)
    fig.savefig(args.output / "comparison.svg")
    print(f"Plotted {len(rows)} recorded measurements: {args.output / 'comparison.png'}")


if __name__ == "__main__":
    main()
