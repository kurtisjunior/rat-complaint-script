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

- **No automatic schedule**
- Manual trigger only via GitHub Actions `workflow_dispatch`
- Must work in GitHub Actions Ubuntu runner environment

---

## Inputs and Configuration

Provide defaults in code, but allow override via environment variables so the workflow can adjust without edits.

| Input | Default | Source |
|-------|---------|--------|
| Address | 333 East 34th Street | env `ADDRESS` |
| City | New York | env `CITY` |
| State | NY | env `STATE` |
| Zip | 10016 | env `ZIP` |
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
| Additional Details | "Trash is out in the open, the bin area is exposed, it attracts a lot of rats every single day" |
| Description | Randomly selected from pre-written list (see below) |
| Date/Time Observed | Auto-generate to current date/time at submission |
| Is this a recurring problem? | Yes |

### Step 2: Where

| Field | Value |
|-------|-------|
| Address | 333 East 34th Street |
| City | New York |
| State | NY |
| Zip | 10016 |

### Step 3: Who

- Leave all contact fields empty (anonymous submission)

### Step 4: Review

- Verify all information is correct
- Submit the complaint

---

## Description Variations

Each submission randomly selects one description from this list:

```python
DESCRIPTIONS = [
    "The trash area behind this building has become a severe public health hazard. Rats are swarming the exposed bins every single day, and I've counted over a dozen running back and forth across the sidewalk during daylight hours. The bins are completely inadequate—they overflow constantly and food waste is left on the ground. Residents including children and elderly people have to walk past this mess daily. This situation has persisted for months and is getting worse. I'm requesting an immediate inspection and enforcement action.",

    "I'm reporting a serious and ongoing rodent infestation at this address caused by grossly inadequate trash management. The garbage area is completely exposed with no proper containment. Rats have taken over—they're bold enough to run across the sidewalk even when people are walking by. Food scraps are scattered on the ground attracting more vermin daily. This is a clear violation of health codes and poses a disease risk to everyone in the area. Please send an inspector as soon as possible.",

    "This location has a dangerous rat problem that requires urgent attention. The trash situation is out of control—bins are overflowing, lids are missing or broken, and food waste is left exposed on the ground. I see rats every single day, often in groups, running through the garbage area and across the public sidewalk. This is happening in broad daylight, which indicates a severe infestation. The building management has done nothing. I'm asking the city to intervene and enforce proper sanitation standards.",

    "The rodent situation at this building has reached a critical level. The trash area is a complete disaster—there aren't nearly enough bins for the building, garbage overflows onto the ground, and food waste attracts swarms of rats daily. I've personally witnessed rats running across the sidewalk while residents try to enter and exit the building. Children live here and have to walk past this health hazard every day. This needs immediate inspection and the property owner must be held accountable.",

    "I'm filing this complaint because the rat infestation at this address is a genuine public health emergency. The trash management is nonexistent—bins are exposed, overflowing, and surrounded by food waste. Rats are everywhere. They run across the sidewalk constantly, sometimes in groups of four or five at a time. I've seen them during morning, afternoon, and evening hours. This isn't just unpleasant—it's a disease vector in a residential area. Please prioritize this for inspection.",

    "The garbage area at this building is creating a massive rat problem that affects the entire block. There are not enough bins, they're always overflowing, and food is scattered on the ground. Rats swarm the area daily and run freely across the sidewalk. I've lived in NYC for years and this is the worst rodent situation I've ever seen. Elderly residents are afraid to take out their trash. This requires immediate enforcement action against the property owner.",

    "Reporting an ongoing health code violation due to severe rodent activity. The trash area is completely exposed and poorly maintained—bins overflow regularly, food waste accumulates on the ground, and rats have infested the area. They run back and forth across the public sidewalk at all hours of the day. This building is in a residential neighborhood with families and children. The unsanitary conditions are unacceptable and the city needs to take action to protect public health.",

    "This address has a persistent rat problem caused by negligent trash management. The bin area is totally exposed with no covers or containment. Garbage overflows constantly and attracts rodents in large numbers. I observe rats running across the sidewalk every single day—sometimes multiple times per day. This has been going on for months with no improvement. The property owner is clearly not maintaining proper sanitation. Please inspect and issue violations as necessary.",

    "The rat infestation at this location is severe and requires immediate city intervention. The root cause is obvious: the trash area is a mess. Bins are inadequate and always overflowing. Food waste is left on the ground. There's no proper containment system. As a result, rats swarm the area daily and run across the sidewalk where residents and pedestrians walk. This is a clear health hazard in a populated area. I'm requesting inspection, enforcement, and follow-up to ensure the problem is resolved.",

    "I'm reporting a serious sanitation issue causing a major rat infestation. The building's trash area is completely exposed and poorly managed. There aren't enough bins, they're constantly overflowing, and food scraps litter the ground. Rats are active throughout the day—I see them running across the sidewalk regularly, sometimes within feet of people walking by. This is disgusting and dangerous. The property needs to be inspected and the owner needs to be required to fix the trash situation immediately.",
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
