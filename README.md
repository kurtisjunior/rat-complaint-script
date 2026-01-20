# NYC 311 Rat Complaint Automation

Manual-triggered submission of rodent complaints to NYC 311 for 333 East 34th Street.

## What it does

- Submits a rat complaint **on demand** via GitHub Actions (manual trigger)
- Fills out the 4-step form: What → Where → Who → Review
- Generates a unique description each time using pre-written random variations
- Runs anonymously (no contact info required)
- Fully automated - no local machine needed

## Complaint Details

| Field | Value |
|-------|-------|
| Address | 333 East 34th Street, New York, NY 10016 |
| Problem Detail | Condition Attracting Rodents |
| Additional Details | Trash is out in the open, the bin area is exposed, it attracts a lot of rats every single day |
| Date/Time Observed | Auto-generated at submission time |
| Recurring Problem | Yes |

## Setup

### 1. Push to GitHub

```bash
git init
git add .
git commit -m "Initial commit"
gh repo create rat-complaint --private --push
```

### 2. Enable Actions

The workflow runs only when you manually trigger it in GitHub Actions.

To run: **Actions → Submit Complaint → Run workflow**

## Files

```
├── .github/
│   └── workflows/
│       └── submit-complaint.yml   # GitHub Actions workflow
├── submit.py                      # Main automation script (Playwright)
├── requirements.txt               # Python dependencies
├── SPEC.md                        # Build specification
└── README.md                      # This file
```

## Local Testing

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Test with dry run (doesn't submit)
python submit.py --dry-run

# Test for real
python submit.py
```
