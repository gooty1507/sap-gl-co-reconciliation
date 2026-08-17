"""
reconcile.py
------------
Reconciles a GL (FI) extract against a CO extract, the way a Finance
Systems Analyst would when checking that Financial Accounting postings
agree with Controlling (cost center) postings.

Break types detected:
    MISSING_IN_CO        - document exists in GL but not in CO
    MISSING_IN_GL         - document exists in CO but not in GL (orphan CO entry)
    AMOUNT_MISMATCH        - same document, amount differs beyond tolerance
    COST_CENTER_MISMATCH   - same document, cost center differs
    DUPLICATE_IN_CO         - document appears more than once in CO

Run:
    python src/reconcile.py
"""

import csv
from collections import defaultdict
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"
OUTPUT_DIR = BASE_DIR / "output"
OUTPUT_DIR.mkdir(exist_ok=True)

AMOUNT_TOLERANCE = 0.01  # dollars


def load_csv(path):
    with open(path, newline="") as f:
        return list(csv.DictReader(f))


def index_by_doc(records):
    idx = defaultdict(list)
    for r in records:
        idx[r["document_number"]].append(r)
    return idx


def main():
    gl_records = load_csv(DATA_DIR / "gl_extract.csv")
    co_records = load_csv(DATA_DIR / "co_extract.csv")

    gl_idx = index_by_doc(gl_records)
    co_idx = index_by_doc(co_records)

    exceptions = []

    # GL -> CO checks
    for doc, gl_matches in gl_idx.items():
        gl_rec = gl_matches[0]
        co_matches = co_idx.get(doc)

        if not co_matches:
            exceptions.append(
                {
                    "document_number": doc,
                    "break_type": "MISSING_IN_CO",
                    "gl_amount": gl_rec["amount"],
                    "co_amount": "",
                    "gl_cost_center": gl_rec["cost_center"],
                    "co_cost_center": "",
                    "variance": gl_rec["amount"],
                    "detail": "Document posted in FI but never reached CO",
                }
            )
            continue

        if len(co_matches) > 1:
            exceptions.append(
                {
                    "document_number": doc,
                    "break_type": "DUPLICATE_IN_CO",
                    "gl_amount": gl_rec["amount"],
                    "co_amount": sum(float(m["amount"]) for m in co_matches),
                    "gl_cost_center": gl_rec["cost_center"],
                    "co_cost_center": co_matches[0]["cost_center"],
                    "variance": round(
                        sum(float(m["amount"]) for m in co_matches) - float(gl_rec["amount"]), 2
                    ),
                    "detail": f"Document appears {len(co_matches)}x in CO extract",
                }
            )

        co_rec = co_matches[0]
        gl_amount = float(gl_rec["amount"])
        co_amount = float(co_rec["amount"])

        if abs(gl_amount - co_amount) > AMOUNT_TOLERANCE:
            exceptions.append(
                {
                    "document_number": doc,
                    "break_type": "AMOUNT_MISMATCH",
                    "gl_amount": gl_amount,
                    "co_amount": co_amount,
                    "gl_cost_center": gl_rec["cost_center"],
                    "co_cost_center": co_rec["cost_center"],
                    "variance": round(co_amount - gl_amount, 2),
                    "detail": "FI and CO amounts do not agree",
                }
            )

        if gl_rec["cost_center"] != co_rec["cost_center"]:
            exceptions.append(
                {
                    "document_number": doc,
                    "break_type": "COST_CENTER_MISMATCH",
                    "gl_amount": gl_amount,
                    "co_amount": co_amount,
                    "gl_cost_center": gl_rec["cost_center"],
                    "co_cost_center": co_rec["cost_center"],
                    "variance": 0,
                    "detail": "Cost center reposted in CO after FI posting",
                }
            )

    # CO -> GL checks (orphans: exist in CO, not in GL at all)
    for doc, co_matches in co_idx.items():
        if doc not in gl_idx:
            co_rec = co_matches[0]
            exceptions.append(
                {
                    "document_number": doc,
                    "break_type": "MISSING_IN_GL",
                    "gl_amount": "",
                    "co_amount": co_rec["amount"],
                    "gl_cost_center": "",
                    "co_cost_center": co_rec["cost_center"],
                    "variance": co_rec["amount"],
                    "detail": "CO-only posting with no corresponding FI document",
                }
            )

    # Write exceptions report
    exceptions_path = OUTPUT_DIR / "exceptions_report.csv"
    fieldnames = [
        "document_number", "break_type", "gl_amount", "co_amount",
        "gl_cost_center", "co_cost_center", "variance", "detail",
    ]
    with open(exceptions_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(exceptions)

    # Summary
    by_type = defaultdict(int)
    total_variance = 0.0
    for e in exceptions:
        by_type[e["break_type"]] += 1
        try:
            total_variance += abs(float(e["variance"]))
        except (TypeError, ValueError):
            pass

    summary_lines = [
        "SAP FI (GL) vs CO Reconciliation Summary",
        "=" * 45,
        f"GL records:        {len(gl_records)}",
        f"CO records:        {len(co_records)}",
        f"Total exceptions:  {len(exceptions)}",
        f"Total variance:    ${total_variance:,.2f}",
        "",
        "Exceptions by type:",
    ]
    for break_type, count in sorted(by_type.items()):
        summary_lines.append(f"  {break_type:<25} {count}")

    summary_path = OUTPUT_DIR / "summary.txt"
    summary_path.write_text("\n".join(summary_lines) + "\n")

    print("\n".join(summary_lines))
    print(f"\nDetailed exceptions written to {exceptions_path}")


if __name__ == "__main__":
    main()
