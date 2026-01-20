#!/usr/bin/env python3
"""
NYC 311 Rat Complaint Automation Script

Submits rodent complaints to NYC 311 via Playwright automation.
Supports anonymous submission with configurable address.
"""

import argparse
import os
import random
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from playwright.sync_api import sync_playwright, expect, TimeoutError as PlaywrightTimeout


# Constants
FORM_DIRECT_URL = (
    "https://portal.311.nyc.gov/sr-step/?id=fb797007-e3f3-f011-92b8-7c1e52e6db72&stepid=4a51f5a5-b04c-e811-a835-000d3a33b1e4"
)
# Main Rat or Mouse Complaint article page (fallback)
FORM_ARTICLE_URL = "https://portal.311.nyc.gov/article/?kanumber=KA-01107"

DESCRIPTIONS = [
    "Rats frequently seen running along the building's foundation and near trash areas.",
    "Multiple rat burrows observed near the property line and sidewalk cracks.",
    "Rodents spotted entering and exiting holes near the building's basement vents.",
    "Rat droppings found regularly along the exterior walls and near garbage bins.",
    "Live rats observed during daylight hours near uncovered trash containers.",
    "Rodent activity increasing - rats seen nightly foraging near the property.",
    "Rat holes and runways visible along the building perimeter and adjacent lots.",
    "Persistent rat infestation with burrows near vegetation and waste areas.",
    "Rats observed accessing the property through gaps in the building foundation.",
    "Regular rodent sightings near improperly stored garbage and debris piles.",
]

ADDITIONAL_DETAILS = "Outdoor, Structure (foundation, around perimeter)"

# Default address (can be overridden via environment variables)
DEFAULT_ADDRESS = "333 East 34th Street"
DEFAULT_CITY = "New York"
DEFAULT_STATE = "NY"
DEFAULT_ZIP = "10016"


def get_config():
    """Get configuration from environment variables with defaults."""
    return {
        "address": os.environ.get("ADDRESS", DEFAULT_ADDRESS),
        "city": os.environ.get("CITY", DEFAULT_CITY),
        "state": os.environ.get("STATE", DEFAULT_STATE),
        "zip": os.environ.get("ZIP", DEFAULT_ZIP),
    }

def get_form_url():
    """Get form URL from environment variables with default direct form link."""
    return os.environ.get("FORM_URL", FORM_DIRECT_URL)


def get_current_datetime_nyc():
    """Returns current date/time in America/New_York timezone."""
    return datetime.now(ZoneInfo("America/New_York"))


def select_random_description():
    """Select a random description from the pre-written variations."""
    return random.choice(DESCRIPTIONS)


def save_debug_artifacts(page, error_name="error"):
    """Save screenshot and HTML on failure to artifacts/ directory."""
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

    # Save screenshot
    screenshot_path = artifacts_dir / f"{error_name}_{timestamp}.png"
    try:
        page.screenshot(path=str(screenshot_path), full_page=True)
        print(f"Screenshot saved: {screenshot_path}")
    except Exception as e:
        print(f"Failed to save screenshot: {e}")

    # Save HTML
    html_path = artifacts_dir / f"{error_name}_{timestamp}.html"
    try:
        html_content = page.content()
        html_path.write_text(html_content)
        print(f"HTML saved: {html_path}")
    except Exception as e:
        print(f"Failed to save HTML: {e}")


def ensure_no_captcha(page):
    """Fail fast if CAPTCHA is detected."""
    captcha_element = page.locator(
        "iframe[src*='recaptcha'], .g-recaptcha, #captcha, [class*='captcha']"
    ).first
    if captcha_element.count() > 0 and captcha_element.is_visible():
        print("ERROR: CAPTCHA detected. Cannot proceed automatically.")
        save_debug_artifacts(page, "captcha_detected")
        raise Exception("CAPTCHA detected")


def wait_for_network_idle(page, timeout=10000):
    """Best-effort wait for network idle without hard-failing."""
    try:
        page.wait_for_load_state("networkidle", timeout=timeout)
    except PlaywrightTimeout:
        pass


def get_current_step(page):
    """Return the current step number (1-4) based on the progress indicator."""
    for step in [1, 2, 3, 4]:
        # Active step typically has a distinct class or aria attribute
        active = page.locator(f".progress-step.active:has-text('{step}'), [aria-current='step']:has-text('{step}')").first
        if active.count() > 0:
            return step
    # Fallback: check for step-specific elements
    if page.locator("#n311_problemdetailid_select").count() > 0:
        return 1
    if page.locator("#n311_locationtypeid_select").count() > 0:
        return 2
    if page.locator("fieldset[aria-label*='Contact'], input[id*='firstname']").first.count() > 0:
        return 3
    if page.get_by_role("button", name="Submit").count() > 0:
        return 4
    return None


def wait_and_click_next(page, expected_next_step=None):
    """Wait for and click the Next/Continue button, then verify step transition."""
    # Try multiple selectors for the Next button
    next_button = page.get_by_role("button", name="Next").first
    if next_button.count() == 0:
        next_button = page.get_by_role("button", name="Continue").first
    if next_button.count() == 0:
        next_button = page.locator(
            "button:has-text('Next'), button:has-text('Continue'), "
            "a:has-text('Next'), a:has-text('Continue'), "
            "input[type='submit'][value*='Next'], input[type='submit'][value*='Continue'], "
            "[role='button']:has-text('Next'), [role='button']:has-text('Continue')"
        ).first

    expect(next_button).to_be_visible(timeout=15000)
    next_button.click()
    wait_for_network_idle(page)

    # Verify we moved to the next step (if specified)
    if expected_next_step:
        page.wait_for_timeout(1000)
        current = get_current_step(page)
        if current and current != expected_next_step:
            save_debug_artifacts(page, f"step_transition_failed_expected_{expected_next_step}")
            raise Exception(f"Step transition failed: expected step {expected_next_step}, got {current}")


def on_complaint_form(page):
    """Determine whether the current page looks like the complaint form."""
    return page.locator("#n311_problemdetailid_select").count() > 0


def navigate_to_complaint_form(page):
    """Navigate from Rat or Mouse Complaint article to the complaint form."""
    print("Navigating to complaint form...")

    if on_complaint_form(page):
        print("  - Already on complaint form")
        return

    if not page.url.startswith(FORM_ARTICLE_URL):
        page.goto(FORM_ARTICLE_URL, wait_until="domcontentloaded")
        wait_for_network_idle(page)

    # Step 1: Expand "Residential Addresses" section
    residential_section = page.locator("text=Residential Addresses").first
    if residential_section.count() > 0:
        expect(residential_section).to_be_visible(timeout=10000)
        residential_section.click()
        print("  - Expanded 'Residential Addresses' section")

    # Step 2: Click the "Report rats or conditions that might attract them." button
    # This is a JavaScript button that triggers createServiceRequest()
    report_button = page.locator("a:has-text('Report rats or conditions that might attract them')").first
    if report_button.count() == 0:
        # Try alternative - look for any DOHMH rat report button in expanded section
        report_button = page.locator("a.btn:has-text('Report rats')").first
    if report_button.count() == 0:
        report_button = page.locator("a[onclick*='createServiceRequest']:has-text('Report rats')").first

    if report_button.count() > 0:
        expect(report_button).to_be_visible(timeout=10000)
        report_button.click()
        wait_for_network_idle(page)
        print("  - Clicked 'Report rats' button")
    else:
        print("  - No 'Report rats' button found")
        save_debug_artifacts(page, "no_report_button")
        raise Exception("Could not find 'Report rats' button")

    # Wait for form to load
    expect(page.locator("#n311_problemdetailid_select")).to_be_visible(timeout=15000)


def fill_step1_what(page, description, nyc_datetime):
    """Step 1: Fill in the 'What' details about the complaint."""
    print("Step 1: Filling complaint details...")

    wait_for_network_idle(page)

    # Select "Condition Attracting Rodents" from Problem Detail dropdown
    problem_detail = page.locator("#n311_problemdetailid_select")
    expect(problem_detail).to_be_visible(timeout=15000)
    problem_detail.select_option(label="Condition Attracting Rodents")
    print("  - Selected 'Condition Attracting Rodents'")

    # Fill Additional Details dropdown (appears after Problem Detail selection)
    additional_details = page.locator("select[id*='additionaldetails'], select[id*='additional']").first
    try:
        additional_details.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeout:
        additional_details = None

    if additional_details and additional_details.count() > 0 and additional_details.is_visible():
        # Try preferred options in order (outdoor-related for rat complaints)
        preferred_options = [
            ADDITIONAL_DETAILS,
            "Outdoor",
            "Outside",
            "Exterior",
            "Foundation",
            "Perimeter",
        ]
        selected = False
        for pref in preferred_options:
            if additional_details.locator(f"option:has-text('{pref}')").count() > 0:
                additional_details.select_option(label=additional_details.locator(f"option:has-text('{pref}')").first.text_content())
                print(f"  - Selected Additional Details: {pref}")
                selected = True
                break

        if not selected:
            # Fallback to first non-empty option
            additional_details.select_option(index=1)
            print("  - Selected Additional Details: (first available)")

    # Fill Description textarea
    description_field = page.get_by_label("Description").first
    if description_field.count() == 0:
        description_field = page.locator("textarea:visible").first
    expect(description_field).to_be_visible(timeout=5000)
    description_field.fill(description)
    print(f"  - Filled Description: {description[:50]}...")

    # Set Date/Time Observed (combined field with format M/D/YYYY h:mm A)
    datetime_str = nyc_datetime.strftime("%-m/%-d/%Y %-I:%M %p")
    datetime_field = page.locator("input[id='n311_datetimeobserved']:visible, input[placeholder*='M/D/YYYY']:visible").first
    if datetime_field.count() > 0:
        expect(datetime_field).to_be_visible(timeout=5000)
        datetime_field.click()
        datetime_field.fill(datetime_str)
        # Press Tab to close any date picker that might open
        datetime_field.press("Tab")
        print(f"  - Set Date/Time Observed: {datetime_str}")

    # Select "Yes" for recurring problem
    recurring_group = page.locator("fieldset:has-text('recurring'), div:has-text('recurring')").first
    if recurring_group.count() > 0:
        yes_radio = recurring_group.get_by_label("Yes")
    else:
        yes_radio = page.get_by_role("radio", name="Yes").first
    if yes_radio.count() > 0:
        yes_radio.check()
        print("  - Selected 'Yes' for recurring problem")

    # Click Next and verify we reach Step 2
    wait_and_click_next(page, expected_next_step=2)
    print("Step 1 complete.")


def fill_step2_where(page, config):
    """Step 2: Fill in the 'Where' location details."""
    print("Step 2: Filling location details...")

    wait_for_network_idle(page)

    # Wait for Location Type dropdown to have options loaded
    # Wait for options to be populated in the dropdown
    page.wait_for_function(
        "document.querySelector('#n311_locationtypeid_select option[value]:not([value=\"\"])') !== null",
        timeout=15000
    )
    print("  - Location Type options loaded")

    # Select Location Type - try multiple options for residential buildings
    location_type = page.locator("#n311_locationtypeid_select")
    expect(location_type).to_be_visible(timeout=10000)

    # Try location types in order of preference
    location_options = [
        "3+ Family Apt. Building",
        "3+ Family Mixed Use Building",
        "1-2 Family Dwelling",
        "1-2 Family Mixed Use Building",
    ]
    selected = False
    for option in location_options:
        if location_type.locator(f"option:has-text('{option}')").count() > 0:
            location_type.select_option(label=option)
            print(f"  - Selected Location Type: {option}")
            selected = True
            break

    if not selected:
        # Fallback: select first non-empty option
        location_type.select_option(index=1)
        print("  - Selected Location Type: (first available)")

    wait_for_network_idle(page)

    # Select Location Detail if present and visible
    location_detail = page.locator("#n311_locationdetailid_select")
    if location_detail.count() > 0 and location_detail.is_visible():
        location_detail.select_option(index=1)
        print("  - Selected Location Detail")
        wait_for_network_idle(page)

    # Look for address section - check if NYC/Non-NYC radio buttons appear
    nyc_radio = page.locator("#n311_portaladdresstype_0")
    if nyc_radio.count() > 0 and nyc_radio.is_visible():
        nyc_radio.click()
        print("  - Selected NYC Address")
        wait_for_network_idle(page)

    # Fill street address - try various possible fields
    address_input = page.get_by_label("Street Address").first
    if address_input.count() == 0:
        address_input = page.locator("input[id*='address']:visible:not([readonly])").first
    if address_input.count() > 0:
        expect(address_input).to_be_visible(timeout=5000)
        address_input.fill(config["address"])
        address_input.press("Tab")
        print(f"  - Filled Address: {config['address']}")
        wait_for_network_idle(page)

    # Fill City/State if visible (for non-NYC or optional fields)
    city_input = page.get_by_label("City").first
    if city_input.count() > 0 and city_input.is_visible():
        city_input.fill(config["city"])
        print(f"  - Filled City: {config['city']}")

    state_input = page.get_by_label("State").first
    if state_input.count() > 0 and state_input.is_visible():
        state_input.fill(config["state"])
        print(f"  - Filled State: {config['state']}")

    # Fill Borough if dropdown is visible
    borough = page.locator("select#n311_boroughid_select:visible").first
    if borough.count() > 0:
        borough.select_option(label="Manhattan")
        print("  - Selected Borough: Manhattan")

    # Fill Zip if visible
    zip_input = page.get_by_label("Zip").first
    if zip_input.count() == 0:
        zip_input = page.locator("input#n311_zipcode:visible").first
    if zip_input.count() > 0:
        zip_input.fill(config["zip"])
        print(f"  - Filled Zip: {config['zip']}")

    # Click Next and verify we reach Step 3
    wait_and_click_next(page, expected_next_step=3)
    print("Step 2 complete.")


def fill_step3_who(page):
    """Step 3: Handle contact information (leave empty for anonymous)."""
    print("Step 3: Skipping contact info (anonymous submission)...")

    wait_for_network_idle(page)

    # Leave all fields empty - anonymous submission is allowed per spec
    # Click Next and verify we reach Step 4 (Review)
    wait_and_click_next(page, expected_next_step=4)
    print("Step 3 complete.")


def fill_step4_review_and_submit(page, dry_run=False):
    """Step 4: Review and submit the complaint."""
    print("Step 4: Review and submit...")

    wait_for_network_idle(page)
    ensure_no_captcha(page)

    # Log what's on the review page
    print("  - Reviewing submission details...")

    if dry_run:
        print("  - DRY RUN: Skipping final submit")
        print("Dry run completed successfully!")
        return True

    # Find and click Submit button
    submit_button = page.get_by_role("button", name="Submit")
    if submit_button.count() == 0:
        submit_button = page.locator("button[type='submit'], input[type='submit']").first

    expect(submit_button).to_be_visible(timeout=10000)
    submit_button.click()
    print("  - Clicked Submit")

    # Wait for confirmation page
    wait_for_network_idle(page)

    # Must find confirmation - check for thank you message or confirmation number
    confirmation_found = False
    confirmation_number = None

    try:
        # Wait for confirmation text to appear
        page.get_by_text("Thank you", exact=False).wait_for(timeout=15000)
        confirmation_found = True
    except PlaywrightTimeout:
        # Check page content as fallback
        page_text = page.content().lower()
        if "thank you" in page_text or "confirmation" in page_text or "submitted" in page_text:
            confirmation_found = True

    if not confirmation_found:
        save_debug_artifacts(page, "submission_failed_no_confirmation")
        raise Exception("Submission failed: no confirmation message found")

    # Try to extract confirmation number
    confirmation_element = page.locator("text=/[A-Z0-9-]{6,}/").first
    if confirmation_element.count() > 0:
        confirmation_number = confirmation_element.text_content().strip()
        print(f"Confirmation number: {confirmation_number}")
    else:
        print("  - No confirmation number found (but submission appears successful)")

    print("Submission confirmed!")
    return True


def main():
    """Main entry point for the automation script."""
    parser = argparse.ArgumentParser(description="Submit NYC 311 Rat Complaint")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Navigate through form but don't submit",
    )
    parser.add_argument(
        "--headed",
        action="store_true",
        help="Run browser in headed mode (visible window)",
    )
    args = parser.parse_args()

    config = get_config()
    nyc_datetime = get_current_datetime_nyc()
    description = select_random_description()

    print("=" * 60)
    print("NYC 311 Rat Complaint Automation")
    print("=" * 60)
    print(f"Time (NYC): {nyc_datetime.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Address: {config['address']}, {config['city']}, {config['state']} {config['zip']}")
    print(f"Dry run: {args.dry_run}")
    print("=" * 60)

    browser = None
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context(timezone_id="America/New_York", locale="en-US")
        page = context.new_page()
        page.set_default_timeout(15000)

        try:
            # Navigate to form
            form_url = get_form_url()
            print(f"Navigating to: {form_url}")
            page.goto(form_url, wait_until="domcontentloaded")
            wait_for_network_idle(page)

            ensure_no_captcha(page)

            # Navigate to the complaint form
            navigate_to_complaint_form(page)
            ensure_no_captcha(page)

            # Execute form steps
            fill_step1_what(page, description, nyc_datetime)
            fill_step2_where(page, config)
            fill_step3_who(page)
            fill_step4_review_and_submit(page, dry_run=args.dry_run)

            print("=" * 60)
            print("SUCCESS: Complaint process completed!")
            print("=" * 60)
            return 0

        except PlaywrightTimeout as e:
            print(f"ERROR: Timeout waiting for element: {e}")
            save_debug_artifacts(page, "timeout_error")
            return 1
        except Exception as e:
            print(f"ERROR: {e}")
            save_debug_artifacts(page, "error")
            return 1
        finally:
            if browser:
                browser.close()


if __name__ == "__main__":
    sys.exit(main())
