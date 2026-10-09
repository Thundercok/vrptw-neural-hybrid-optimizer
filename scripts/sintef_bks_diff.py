"""Compare configured BKS values against the recorded SINTEF reference."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from vrptw.config import BKS as LOCAL_BKS


def generate_diff_report(output_md_path: str = "results/sintef_bks_diff.md") -> dict:
    ref_file = ROOT / "data" / "reference" / "sintef_official_bks.json"
    if not ref_file.exists():
        raise FileNotFoundError(f"Reference SINTEF file missing: {ref_file}")

    with open(ref_file, encoding="utf-8") as f:
        data = json.load(f)

    meta = data.get("_metadata", {})
    sintef_bks = data.get("instances", {})

    total_sintef = len(sintef_bks)
    mismatches = []
    missing_in_local = []
    matched = []

    tol_td = 0.01

    for name, ref in sintef_bks.items():
        local = LOCAL_BKS.get(name)
        if local is None:
            missing_in_local.append(
                {
                    "instance": name,
                    "sintef_nv": ref["nv"],
                    "sintef_td": ref["td"],
                    "citation": ref.get("full_citation", "SINTEF"),
                }
            )
            continue

        nv_diff = local["nv"] != ref["nv"]
        delta_pct = (local["td"] - ref["td"]) / ref["td"] * 100.0
        abs_delta = abs(delta_pct)
        td_diff = abs_delta > tol_td

        if nv_diff or td_diff:
            mismatches.append(
                {
                    "instance": name,
                    "local_nv": local["nv"],
                    "sintef_nv": ref["nv"],
                    "local_td": local["td"],
                    "sintef_td": ref["td"],
                    "delta_pct": round(delta_pct, 4),
                    "nv_diff": nv_diff,
                    "td_diff": td_diff,
                    "citation": ref.get("full_citation", "SINTEF"),
                }
            )
        else:
            matched.append(
                {"instance": name, "nv": ref["nv"], "td": ref["td"], "citation": ref.get("full_citation", "SINTEF")}
            )

    lines = [
        "# BKS Comparison",
        "",
        f"Reference: `data/reference/sintef_official_bks.json` ({meta.get('timestamp_utc', 'undated')}).",
        f"Instances: {total_sintef} reference, {len(LOCAL_BKS)} local.",
        f"Matches within 0.01% distance tolerance and equal fleet size: {len(matched)}.",
        f"Mismatches: {len(mismatches)}. Missing local entries: {len(missing_in_local)}.",
    ]
    if mismatches:
        lines += [
            "",
            "| Instance | Local NV | Reference NV | Local TD | Reference TD | TD delta (%) |",
            "| --- | --- | --- | --- | --- | --- |",
        ]
        for row in mismatches:
            lines.append(
                f"| {row['instance']} | {row['local_nv']} | {row['sintef_nv']} | "
                f"{row['local_td']:.2f} | {row['sintef_td']:.2f} | {row['delta_pct']:+.4f} |"
            )
    if missing_in_local:
        lines += ["", "Missing: " + ", ".join(row["instance"] for row in missing_in_local) + "."]

    out_file = ROOT / output_md_path
    out_file.parent.mkdir(parents=True, exist_ok=True)
    out_file.write_text("\n".join(lines), encoding="utf-8")
    print(f"Audit report generated at: {out_file}")

    return {
        "total_sintef": total_sintef,
        "total_local": len(LOCAL_BKS),
        "mismatches": len(mismatches),
        "missing": len(missing_in_local),
    }


if __name__ == "__main__":
    generate_diff_report()
