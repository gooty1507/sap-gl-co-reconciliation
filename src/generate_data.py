"""
generate_data.py
-----------------
Generates synthetic GL (General Ledger, FI module) and CO (Controlling module,
cost center) extracts shaped like real SAP data, with realistic reconciliation
breaks baked in on purpose so reconcile.py has something to find.

Run:
    python src/generate_data.py
"""

import random
import csv
from datetime import date, timedelta
from pathlib import Path

random.seed(42)

DATA_DIR = Path(__file__).resolve().parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)

COST_CENTERS = [f"CC{n:04d}" for n in range(1000, 1030)]
GL_ACCOUNTS = [
    "400000", "400100", "410000", "420000", "430000",
    "610000", "620000", "630000", "710000", "720000",
]
VENDORS = [f"V{n:05d}" for n in range(10000, 10040)]
COMPANY_CODES = ["1000", "2000"]

START_DATE = date(2026, 1, 1)
NUM_GL_RECORDS = 500


def random_date():
    offset = random.randint(0, 210)  # ~7 months of postings
    return START_DATE + timedelta(days=offset)


def make_gl_record(doc_number):
    amount = round(random.uniform(50, 25000), 2)
    return {
        "document_number": f"DOC{doc_number:07d}",
        "company_code": random.choice(COMPANY_CODES),
        "posting_date": random_date().isoformat(),
        "gl_account": random.choice(GL_ACCOUNTS),
        "cost_center": random.choice(COST_CENTERS),
        "vendor": random.choice(VENDORS),
        "amount": amount,
        "currency": "USD",
        "document_type": random.choice(["KR", "SA", "KZ"]),
    }


def main():
    gl_records = [make_gl_record(100000 + i) for i in range(NUM_GL_RECORDS)]

    # Build the CO extract from the GL records, then intentionally break it
    co_records = []
    for rec in gl_records:
        co_records.append(
            {
                "document_number": rec["document_number"],
                "cost_center": rec["cost_center"],
                "posting_date": rec["posting_date"],
                "gl_account": rec["gl_account"],
                "amount": rec["amount"],
            }
        )

    # --- Bake in realistic breaks -------------------------------------
    # 1. Missing in CO: drop ~3% of records entirely (postings that never
    #    made it from FI to CO, e.g. real-time integration failure)
    drop_count = int(NUM_GL_RECORDS * 0.03)
    for rec in random.sample(co_records, drop_count):
        co_records.remove(rec)

    # 2. Amount mismatches: ~4% get a small variance (rounding / currency
    #    translation differences)
    for rec in random.sample(co_records, int(NUM_GL_RECORDS * 0.04)):
        rec["amount"] = round(rec["amount"] + random.choice([-0.5, 0.75, -12.30, 5.00]), 2)

    # 3. Cost center reassignment: ~3% posted to a different cost center in
    #    CO than in FI (manual CO repost after the fact)
    for rec in random.sample(co_records, int(NUM_GL_RECORDS * 0.03)):
        rec["cost_center"] = random.choice(COST_CENTERS)

    # 4. Duplicate postings in CO: ~2% duplicated (double CO allocation run)
    dup_sample = random.sample(co_records, int(NUM_GL_RECORDS * 0.02))
    co_records.extend([dict(r) for r in dup_sample])

    # 5. Orphan CO records with no matching GL document (manual CO-only
    #    journal entries): add a handful
    for i in range(6):
        co_records.append(
            {
                "document_number": f"DOC{900000 + i:07d}",
                "cost_center": random.choice(COST_CENTERS),
                "posting_date": random_date().isoformat(),
                "gl_account": random.choice(GL_ACCOUNTS),
                "amount": round(random.uniform(50, 5000), 2),
            }
        )

    random.shuffle(co_records)

    gl_path = DATA_DIR / "gl_extract.csv"
    co_path = DATA_DIR / "co_extract.csv"

    with open(gl_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(gl_records[0].keys()))
        writer.writeheader()
        writer.writerows(gl_records)

    with open(co_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=list(co_records[0].keys()))
        writer.writeheader()
        writer.writerows(co_records)

    print(f"Wrote {len(gl_records)} GL records to {gl_path}")
    print(f"Wrote {len(co_records)} CO records to {co_path}")


if __name__ == "__main__":
    main()
