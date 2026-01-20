# NYC 311 Rat Complaint Automation

Automated submission of rodent complaints to NYC 311 for 932 Carroll St, Brooklyn.

## What it does

- Submits a rat complaint **every Wednesday at 12:47pm EST**
- Also supports **manual trigger** via GitHub Actions
- Fills out the 4-step form: What → Where → Who → Review
- Generates a unique description each time from pre-written variations
- Runs anonymously (no contact info required)
- Sends **ntfy notification** on success or failure
- Fully automated - no local machine needed

## Complaint Details

| Field | Value |
|-------|-------|
| Address | 932 Carroll St, Brooklyn, NY 11225 |
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

### 2. Add ntfy secret

1. Go to **Settings → Secrets and variables → Actions**
2. Click **New repository secret**
3. Name: `NTFY_TOPIC`, Value: your ntfy topic name

### 3. Run

- **Automatic:** Runs every Wednesday 12-1pm EST
- **Manual:** Actions → Submit Complaint → Run workflow

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

## Roadmap

### Clawd.bot Integration with Photo Support

**Goal:** Send a photo of a rat problem via Telegram/Discord/etc. and have the complaint auto-submit with the image attached.

**Implementation Plan:**

1. **Add `--image` flag to submit.py**
   - Accept a file path: `python submit.py --image /path/to/rat-photo.jpg`
   - In Step 1, click "Add Attachment" button and upload the file
   - Support common formats: jpg, png, heic

2. **Create Clawd.bot skill**
   ```
   When I send a photo with "rat complaint" or "311":
   1. Save the image to /tmp/rat-complaint-{timestamp}.jpg
   2. Run: python submit.py --image /tmp/rat-complaint-{timestamp}.jpg
   3. Reply with confirmation number or error
   ```

3. **Alternative: Direct form filling**
   - Clawd.bot can browse and fill forms directly
   - Could skip the script entirely and just instruct Clawd to fill the 311 form
   - Less reliable but more flexible

**Status:** Not started
