# SAP GL/CO Reconciliation Tool

A Python tool that reconciles SAP Financial Accounting (FI / General Ledger)
postings against SAP Controlling (CO / cost center) postings, and produces
an exception report of the breaks — the same type of check a Finance
Systems Analyst runs during month-end close, S/4HANA cutover validation, or
day-to-day FI-CO integration monitoring.

## Why this project

In SAP, every FI document that hits a cost-center-relevant GL account is
expected to generate a matching CO posting. In practice, integration
failures, manual CO reposts, duplicate allocation runs, and rounding/
currency-translation differences all create breaks between the two ledgers.
Finding and explaining those breaks is a routine, high-value task for a
FICO / Finance Systems Analyst. This project simulates that workflow
end-to-end with realistic (synthetic) data.

## What it does

1. `src/generate_data.py` generates synthetic GL and CO extracts shaped
   like real SAP data — document number, company code, cost center, GL
   account, vendor, amount, posting date — and intentionally bakes in five
   kinds of realistic reconciliation breaks.
2. `src/reconcile.py` matches the two extracts on document number and
   flags every exception it finds.
3. Results land in `output/exceptions_report.csv` (line-item detail) and
   `output/summary.txt` (counts and total variance by break type).

## Break types detected

| Break type              | Meaning                                                            |
|--------------------------|---------------------------------------------------------------------|
| `MISSING_IN_CO`           | Document posted in FI but never reached CO (integration failure)   |
| `MISSING_IN_GL`           | CO-only posting with no matching FI document (manual CO entry)     |
| `AMOUNT_MISMATCH`          | Same document, but FI and CO amounts disagree                      |
| `COST_CENTER_MISMATCH`     | Same document, but cost center differs between FI and CO           |
| `DUPLICATE_IN_CO`           | Document appears more than once in the CO extract                  |

## Project structure

```
sap-gl-co-reconciliation/
├── data/                   # Synthetic GL & CO extracts (CSV)
├── src/
│   ├── generate_data.py    # Regenerate or swap in your own extracts
│   └── reconcile.py        # The matching / exception-detection engine
├── output/                 # Exceptions report + summary (generated)
├── requirements.txt
└── README.md
```

## Getting started

```bash
python -m venv venv
source venv/bin/activate        # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 1. Generate (or regenerate) the synthetic extracts
python src/generate_data.py

# 2. Run the reconciliation
python src/reconcile.py
```

Swap `data/gl_extract.csv` and `data/co_extract.csv` for real (anonymized)
SAP extracts and the reconciliation logic works unchanged — the column
names (`document_number`, `cost_center`, `gl_account`, `amount`,
`posting_date`) match standard SAP FI/CO extract fields.

## Sample output

Running the reconciliation against the included synthetic dataset
(500 GL records) flags roughly 65-80 exceptions across all five break types,
with a few hundred thousand dollars of total variance — see
`output/summary.txt` for the exact numbers from the last run.

## Possible next steps

- Load `output/exceptions_report.csv` into Power BI / Tableau for a
  visual exception dashboard (by cost center, by break type, by period).
- Add a tolerance-band configuration so small rounding differences are
  auto-cleared instead of flagged.
- Extend matching to a two-key match (document number + line item) for
  extracts with multiple line items per document.

## Tech stack

Python 3, `csv`/`pathlib` standard library only (no external dependencies
required to run — `requirements.txt` is provided for optional pandas-based
extensions).
