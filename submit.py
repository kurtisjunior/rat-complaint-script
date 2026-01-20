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
# Main Rat or Mouse Complaint article page
FORM_URL = "https://portal.311.nyc.gov/article/?kanumber=KA-01107"

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


def wait_and_click_next(page):
    """Wait for and click the Next/Continue button."""
    next_button = page.get_by_role("button", name="Next")
    expect(next_button).to_be_visible(timeout=10000)
    next_button.click()
    page.wait_for_load_state("networkidle")


def navigate_to_complaint_form(page):
    """Navigate from Rat or Mouse Complaint article to the complaint form."""
    print("Navigating to complaint form...")

    # Step 1: Expand "Residential Addresses" section
    residential_section = page.locator("text=Residential Addresses").first
    if residential_section.count() > 0:
        expect(residential_section).to_be_visible(timeout=10000)
        residential_section.click()
        page.wait_for_timeout(1500)  # Wait for accordion to expand
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
        page.wait_for_load_state("networkidle")
        print("  - Clicked 'Report rats' button")
    else:
        print("  - No 'Report rats' button found")
        save_debug_artifacts(page, "no_report_button")
        raise Exception("Could not find 'Report rats' button")

    # Wait for form to load
    page.wait_for_timeout(2000)


def fill_step1_what(page, description, nyc_datetime):
    """Step 1: Fill in the 'What' details about the complaint."""
    print("Step 1: Filling complaint details...")

    page.wait_for_load_state("networkidle")

    # Select "Condition Attracting Rodents" from Problem Detail dropdown
    problem_detail = page.locator("#n311_problemdetailid_select")
    expect(problem_detail).to_be_visible(timeout=15000)
    problem_detail.select_option(label="Condition Attracting Rodents")
    print("  - Selected 'Condition Attracting Rodents'")

    # Wait for form to update after selection (Additional Details appears)
    page.wait_for_timeout(1500)

    # Fill Additional Details dropdown (appears after Problem Detail selection)
    additional_details = page.locator("select[id*='additionaldetails'], select[id*='additional']").first
    if additional_details.count() > 0 and additional_details.is_visible():
        # Select the outdoor/structure option
        additional_details.select_option(index=1)  # First non-empty option
        print("  - Selected Additional Details option")
        page.wait_for_timeout(500)

    # Fill Description textarea
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
    yes_label = page.locator("label").filter(has_text="Yes").last
    if yes_label.count() > 0:
        yes_label.click()
        print("  - Selected 'Yes' for recurring problem")

    # Click Next
    wait_and_click_next(page)
    print("Step 1 complete.")


def fill_step2_where(page, config):
    """Step 2: Fill in the 'Where' location details."""
    print("Step 2: Filling location details...")

    page.wait_for_load_state("networkidle")

    # Wait for Location Type dropdown to have options loaded
    page.wait_for_timeout(3000)  # Give time for dynamic content to load

    # Wait for options to be populated in the dropdown
    page.wait_for_function(
        "document.querySelector('#n311_locationtypeid_select option[value]:not([value=\"\"])') !== null",
        timeout=15000
    )
    print("  - Location Type options loaded")

    # Select Location Type - "3+ Family Apt. Building" for residential rat complaints
    location_type = page.locator("#n311_locationtypeid_select")
    expect(location_type).to_be_visible(timeout=10000)
    location_type.select_option(label="3+ Family Apt. Building")
    print("  - Selected Location Type: 3+ Family Apt. Building")
    page.wait_for_timeout(2000)  # Wait for form to update

    # Select Location Detail if present and visible
    location_detail = page.locator("#n311_locationdetailid_select")
    if location_detail.count() > 0 and location_detail.is_visible():
        page.wait_for_timeout(1000)
        location_detail.select_option(index=1)
        print("  - Selected Location Detail")
        page.wait_for_timeout(1500)

    # Look for address section - check if NYC/Non-NYC radio buttons appear
    nyc_radio = page.locator("#n311_portaladdresstype_0")
    if nyc_radio.count() > 0 and nyc_radio.is_visible():
        nyc_radio.click()
        print("  - Selected NYC Address")
        page.wait_for_timeout(1000)

    # Fill street address - try various possible fields
    address_input = page.locator("input#n311_address:visible").first
    if address_input.count() == 0:
        address_input = page.locator("input[id*='address']:visible:not([readonly])").first
    if address_input.count() > 0:
        expect(address_input).to_be_visible(timeout=5000)
        address_input.fill(config["address"])
        address_input.press("Tab")
        print(f"  - Filled Address: {config['address']}")
        page.wait_for_timeout(1000)

    # Fill Borough if dropdown is visible
    borough = page.locator("select#n311_boroughid_select:visible").first
    if borough.count() > 0:
        borough.select_option(label="Manhattan")
        print("  - Selected Borough: Manhattan")
        page.wait_for_timeout(500)

    # Fill Zip if visible
    zip_input = page.locator("input#n311_zipcode:visible").first
    if zip_input.count() > 0:
        zip_input.fill(config["zip"])
        print(f"  - Filled Zip: {config['zip']}")

    # Click Next
    wait_and_click_next(page)
    print("Step 2 complete.")


def fill_step3_who(page):
    """Step 3: Handle contact information (leave empty for anonymous)."""
    print("Step 3: Skipping contact info (anonymous submission)...")

    page.wait_for_load_state("networkidle")

    # Leave all fields empty - anonymous submission is allowed per spec
    # Just click Next to proceed
    wait_and_click_next(page)
    print("Step 3 complete.")


def fill_step4_review_and_submit(page, dry_run=False):
    """Step 4: Review and submit the complaint."""
    print("Step 4: Review and submit...")

    page.wait_for_load_state("networkidle")

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

    # Wait for confirmation
    page.wait_for_load_state("networkidle")
    page.wait_for_timeout(3000)  # Extra wait for confirmation to appear

    # Try to find confirmation number
    page_text = page.content()
    if "confirmation" in page_text.lower() or "thank you" in page_text.lower():
        print("Submission appears successful!")

        # Try to extract confirmation number
        confirmation_element = page.locator("text=/[A-Z0-9]{6,}/").first
        if confirmation_element.count() > 0:
            confirmation_text = confirmation_element.text_content()
            print(f"Confirmation number: {confirmation_text}")

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

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=not args.headed)
        context = browser.new_context()
        page = context.new_page()

        try:
            # Navigate to form
            print(f"Navigating to: {FORM_URL}")
            page.goto(FORM_URL, wait_until="networkidle")

            # Check for CAPTCHA (look for actual CAPTCHA elements, not just the word in page source)
            captcha_element = page.locator("iframe[src*='recaptcha'], .g-recaptcha, #captcha, [class*='captcha']").first
            if captcha_element.count() > 0 and captcha_element.is_visible():
                print("ERROR: CAPTCHA detected. Cannot proceed automatically.")
                save_debug_artifacts(page, "captcha_detected")
                return 1

            # Navigate to the complaint form
            navigate_to_complaint_form(page)

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
            browser.close()


if __name__ == "__main__":
    sys.exit(main())
