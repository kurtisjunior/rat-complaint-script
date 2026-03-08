# NYC 311 Rat Complaint Automation - Build Specification

Build an automated NYC 311 rat complaint submission system that runs on GitHub Actions.

## Goals

- Submit a single complaint per manual workflow run
- Keep inputs explicit and auditable
- Provide a deterministic success/failure signal in CI logs

## Target Form

- **URL**: `https://portal.311.nyc.gov/sr-step/?id=fb797007-e3f3-f011-92b8-7c1e52e6db72&stepid=4a51f5a5-b04c-e811-a835-000d3a33b1e4`
- **Form Flow**: 4 steps - What → Where → Who → Review

## Trigger

- Runs on a schedule via GitHub Actions `schedule` (cron)
- Also supports manual trigger via GitHub Actions `workflow_dispatch`
- Must work in GitHub Actions Ubuntu runner environment

Schedule:

- Every Monday, Wednesday, and Thursday at one random time between 11:00am and 3:00pm ET

---

## Inputs and Configuration

Provide defaults in code, but allow override via environment variables so the workflow can adjust without edits.

| Input | Default | Source |
|-------|---------|--------|
| Address | 932 Carroll St | env `ADDRESS` |
| City | Brooklyn | env `CITY` |
| State | NY | env `STATE` |
| Zip | 11225 | env `ZIP` |
| Problem Detail | Condition Attracting Rodents | constant |
| Additional Details | (see below) | constant |
| Recurring | Yes | constant |
| Dry run | false | CLI flag `--dry-run` |

Use local time in `America/New_York` for date/time observed.

---

## Form Field Values

### Step 1: What

| Field | Value |
|-------|-------|
| Problem Detail | "Condition Attracting Rodents" (dropdown) |
| Additional Details | Selected from the form's dropdown (script attempts a trash/garbage-related option) |
| Description | Randomly selected from pre-written list (see below) |
| Date/Time Observed | Auto-generate to current date/time at submission |
| Is this a recurring problem? | Yes |

### Step 2: Where

| Field | Value |
|-------|-------|
| Address | 932 Carroll St |
| City | Brooklyn |
| State | NY |
| Zip | 11225 |

### Step 3: Who

- Leave all contact fields empty (anonymous submission)

### Step 4: Review

- Verify all information is correct
- Submit the complaint

---

## Description Variations

Each submission randomly selects one description from a pre-written list with stronger tenant-rights and enforcement-focused language.

```python
DESCRIPTIONS = [
    "Rats are out in the open every day now. I routinely see 5+ rats sprinting along the sidewalk between the exposed trash area and underneath parked cars, then back to loose trash on the street. The stench from the open garbage is nauseating and the situation is rapidly getting worse.",
    "This is a blatant and worsening rat infestation. At least 5 rats at a time run in broad daylight from the open trash area, across the sidewalk, and under cars to reach trash left out on the street. The trash area reeks and is completely exposed.",
    "Rats are now active in the daytime and it is escalating. I see them running the sidewalk like a corridor, darting between the open trash area and trash on the street, then disappearing under cars. They also run into the court area where they sleep.",
    "The trash is out in the open and the smell is putrid. Multiple rats (often 5+) are visible at once, running between the trash area and the street, crossing the sidewalk and slipping under parked cars. This is getting worse week by week.",
    "Severe rodent activity: rats are openly running on the sidewalk in daylight. They go back and forth between exposed garbage in the trash area and loose trash on the street, using the space under cars as cover. The court area is now a clear nesting/sleeping spot.",
    "The garbage area is uncovered, overflowing, and foul-smelling. I regularly observe 5+ rats at a time racing from the trash area across the sidewalk, under cars, and toward trash left on the street. They then run into the court area where they sleep.",
    "This location has become a disgusting rat runway. In broad daylight, rats run between the open trash area and trash on the street, crossing the sidewalk and ducking under parked cars. The odor is rancid and the infestation is worsening.",
    "Rats are out in the open and multiplying. I see groups of 5+ running from the exposed trash area to street trash, cutting across the sidewalk and hiding under cars. They also run into the court area where they sleep, and it is getting worse fast.",
    "The trash is stored out in the open and the smell is overwhelming. Rats are now bold in the daytime, running between the trash area and street trash, crossing the sidewalk and moving under parked cars. The court area has active rat traffic and appears to be where they sleep.",
    "This is an urgent sanitation hazard. The exposed trash area stinks, and I repeatedly see 5+ rats at once running the sidewalk between the trash area, under cars, and to trash on the street. They retreat into the court area where they sleep, and the problem is worsening.",
]
```

**Implementation requirements:**
- Use `random.choice()` to select one description per submission
- No external API needed - fully self-contained
- Seed randomness per run only (no per-field re-rolls)

---

## Technical Implementation

### Technology Stack

- **Language**: Python 3.11
- **Browser Automation**: Playwright (headless Chromium)
- **CI/CD**: GitHub Actions

### Dependencies

```
playwright
```

### Files to Create

```
├── .github/
│   └── workflows/
│       └── submit-complaint.yml   # GitHub Actions workflow
├── submit.py                      # Main automation script
├── requirements.txt               # Python dependencies
└── README.md                      # Setup and usage instructions
```

---

## Implementation Tasks

### 1. Form Analysis

- Load the form URL in Playwright (headless mode)
- Navigate through all 4 steps (What, Where, Who, Review) to map fields
- Document all input fields, dropdowns, checkboxes with robust selectors (prefer `get_by_label` and `get_by_role` over CSS)
- Identify any CSRF tokens or session requirements
- Check if a CAPTCHA exists and document expected behavior (do not attempt bypass)

### 2. Build `submit.py`

Create the main Python script with:

- Playwright browser automation (headless Chromium)
- Multi-step wizard flow handling:
  - **Step 1 (What)**: Select problem type, fill details, add description, set date/time, mark recurring
  - **Step 2 (Where)**: Fill address fields
  - **Step 3 (Who)**: Skip/leave empty for anonymous
  - **Step 4 (Review)**: Verify and submit
- `--dry-run` flag for testing without actual submission
- Proper error handling and logging
- Description generation using `random.choice()` from the pre-written list
- Explicit waits for navigation and step completion (avoid fixed sleeps)
- On failure, capture a screenshot and page HTML in `artifacts/`
- Return non-zero exit code on failure, zero on success
- Log the confirmation number if present on the success page

### 3. Build GitHub Actions Workflow

Create `.github/workflows/submit-complaint.yml`:

```yaml
name: Submit Complaint

on:
  workflow_dispatch:  # Manual trigger only

jobs:
  submit:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.11'

      - name: Install dependencies
        run: |
          pip install -r requirements.txt
          playwright install chromium

      - name: Submit complaint
        run: python submit.py
        env:
          ADDRESS: "333 East 34th Street"
          CITY: "New York"
          STATE: "NY"
          ZIP: "10016"
```

### 4. Create `requirements.txt`

```
playwright
```

### 5. Update `README.md`

Include:
- What the project does
- Complaint details table
- Setup instructions (git init, push to GitHub)
- How to run manually via GitHub Actions
- Local testing instructions with `--dry-run`
- Notes about CAPTCHA limitations and expected manual intervention if required

---

## Constraints

- Must work in GitHub Actions Ubuntu runner (headless, no display)
- Keep dependencies minimal (just Playwright)
- Use headless browser only
- No external APIs for description generation
- No automated scheduling

---

## Success Criteria

- Workflow run completes with exit code 0 and logs a confirmation number, or
- Workflow fails with a clear error message and saves artifacts for debugging

---

## Testing Checklist

1. Test script locally with `--dry-run` flag
2. Test full local submission (watch it complete)
3. Push to GitHub
4. Manually trigger workflow via Actions tab
5. Verify logs show successful submission
