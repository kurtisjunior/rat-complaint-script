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
    "Rats are constantly in the front of this building, running in and out of the open garbage. The trash area is a complete mess with overflowing bags and no proper closed bins. I see rats climbing inside the garbage bags daily. The building next door has proper bins with lids and their garbage area is clean - they don't have this problem. This building needs actual closed containers.",

    "There is a severe rat problem at the front of this building due to the garbage situation. The rats are literally inside the open trash bags eating and nesting. The garbage area is filthy and disorganized with nowhere near enough bins, and the ones they have don't close. Meanwhile the neighboring building has enclosed bins and no rat issue. Please inspect and require proper waste management.",

    "Every day I see rats running around the front of this building and going in and out of the exposed garbage. The trash area is disgusting - bags are piled up, bins are overflowing, and nothing is properly covered. The building right next door has their garbage under control with closed bins and I never see rats there. This property needs to be cited for the unsanitary conditions.",

    "The rat infestation at the front of this building is out of control. The rodents are bold enough to climb inside the open garbage in broad daylight. There aren't enough bins and the trash area is always a mess with bags torn open. It's embarrassing because the building next door manages their waste properly with sealed containers and has no visible rat activity. This needs immediate attention.",

    "Rats have taken over the front garbage area of this building. I regularly see them inside the open trash, eating and running around. The waste management here is terrible - not enough bins, no lids, garbage strewn everywhere. The adjacent building has proper enclosed bins and a clean garbage area with no rat problem. This building is creating a health hazard for the entire block.",

    "The front of this building has become a feeding ground for rats due to the deplorable garbage situation. Rats go in and out of the open trash constantly. The bin area is messy, overcrowded, and lacks proper closed containers. Compare this to the building next door which has adequate sealed bins and no rodent issue. The difference is obvious and this property needs to fix their waste storage immediately.",

    "I'm reporting a serious rat problem at the front of this building caused by inadequate garbage management. Rats are seen daily inside the exposed trash bags. The garbage area is in terrible condition with insufficient bins and no covers. The neighboring property has proper closed bins and keeps their area clean - they don't have rats. This building needs to be held accountable.",

    "Rats are infesting the front garbage area of this building. They climb in and out of the open trash bags throughout the day. The waste area is a disaster - messy, overflowing, with not nearly enough enclosed bins. The building next door proves this is fixable - they have proper sealed containers and a clean garbage area with no rat activity. Please require this property to address the sanitation failure.",

    "The rat situation at the front of this building is unacceptable. Rodents are constantly in the open garbage, and the trash area is filthy and disorganized. There are not enough bins and none of them close properly. The building next door has it figured out with adequate closed bins and no rat problem. This property's negligent waste management is attracting vermin to the entire neighborhood.",

    "Reporting ongoing rat activity at the front of this building. The rats are inside the open garbage bags daily - I've seen them crawling in and out numerous times. The garbage area is a mess with overflowing uncovered bins and loose bags everywhere. The adjacent building has proper enclosed bins and maintains a clean waste area with no visible rats. This property needs immediate inspection and enforcement.",
]

ADDITIONAL_DETAILS = "Trash, Improper garbage storage or disposal, Open lot"

# Default address (can be overridden via environment variables)
DEFAULT_ADDRESS = "932 Carroll St"
DEFAULT_CITY = "Brooklyn"
DEFAULT_STATE = "NY"
DEFAULT_ZIP = "11225"


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


def save_submission_details(config, description, nyc_datetime):
    """Save submission details to a file for notification."""
    artifacts_dir = Path("artifacts")
    artifacts_dir.mkdir(exist_ok=True)

    details = f"""Address: {config['address']}, {config['city']}, {config['state']} {config['zip']}
Location Type: 3+ Family Apt. Building
Problem Detail: Condition Attracting Rodents
Additional Details: Garbage
Date/Time Observed: {nyc_datetime.strftime('%-m/%-d/%Y %-I:%M %p')}
Recurring: Yes

Description: {description}"""

    details_path = artifacts_dir / "submission_details.txt"
    details_path.write_text(details)
    print(f"Submission details saved: {details_path}")


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
    # Look for actual reCAPTCHA elements that are visible and have size
    captcha_selectors = [
        "iframe[src*='recaptcha']",
        ".g-recaptcha",
        "#captcha",
        "[class*='recaptcha']",
    ]
    for selector in captcha_selectors:
        captcha_element = page.locator(selector).first
        if captcha_element.count() > 0:
            try:
                # Check if it's actually visible and has dimensions
                if captcha_element.is_visible():
                    box = captcha_element.bounding_box()
                    if box and box['width'] > 50 and box['height'] > 50:
                        print("ERROR: CAPTCHA detected. Cannot proceed automatically.")
                        save_debug_artifacts(page, "captcha_detected")
                        raise Exception("CAPTCHA detected")
            except Exception:
                pass  # Element not interactable, skip


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
        # Try preferred options in order (trash/garbage-related for rat complaints)
        preferred_options = [
            ADDITIONAL_DETAILS,
            "Trash",
            "Garbage",
            "Improper",
            "Open lot",
            "Food",
            "Waste",
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

    # Select Location Detail - required to enable the Address field
    location_detail = page.locator("#n311_locationdetailid_select")
    if location_detail.count() > 0:
        # Wait for Location Detail options to load
        try:
            page.wait_for_function(
                "document.querySelector('#n311_locationdetailid_select option[value]:not([value=\"\"])') !== null",
                timeout=10000
            )
            # Try to select appropriate option for building exterior
            detail_options = ["Exterior", "Outside", "Sidewalk", "Street", "Front", "Building"]
            selected = False
            for opt in detail_options:
                if location_detail.locator(f"option:has-text('{opt}')").count() > 0:
                    location_detail.select_option(label=location_detail.locator(f"option:has-text('{opt}')").first.text_content())
                    print(f"  - Selected Location Detail: {opt}")
                    selected = True
                    break
            if not selected:
                location_detail.select_option(index=1)
                print("  - Selected Location Detail: (first available)")
            wait_for_network_idle(page)
            # Wait for address field to become enabled
            page.wait_for_timeout(1000)
        except PlaywrightTimeout:
            print("  - Location Detail options did not load")

    # Fill the Address lookup field
    # Click the address search button (inside the form, not header)
    search_btn = page.locator("#SelectAddressWhere, .address-picker-btn").first
    expect(search_btn).to_be_visible(timeout=5000)
    search_btn.click()
    wait_for_network_idle(page)
    print("  - Opened address search")

    # Wait for modal/search input to appear - use the specific ID
    modal_input = page.locator("#address-search-box-input").first
    try:
        modal_input.wait_for(state="visible", timeout=5000)

        # Clear and focus the input field
        modal_input.click()
        # Triple-click to select all (works on all platforms)
        modal_input.click(click_count=3)
        page.wait_for_timeout(200)
        modal_input.press("Backspace")  # Clear
        page.wait_for_timeout(500)

        # Type address slowly to trigger autocomplete
        address_text = config['address']
        modal_input.type(address_text, delay=100)  # Type with delay to trigger autocomplete
        print(f"  - Typed address: {address_text}")
        page.wait_for_timeout(1000)  # Wait for autocomplete to react

        # Wait for autocomplete suggestions to appear
        autocomplete_list = page.locator(".ui-autocomplete, .ui-menu").first
        try:
            autocomplete_list.wait_for(state="visible", timeout=5000)
            print("  - Autocomplete suggestions appeared")

            # Wait a moment for all suggestions to load
            page.wait_for_timeout(500)

            # Click on the first address suggestion (should match our typed address)
            # Look for suggestions containing the street name in any borough
            suggestions = page.locator(".ui-menu-item, .ui-autocomplete li").all()
            selected_suggestion = False
            for suggestion in suggestions:
                text = suggestion.text_content() or ""
                # Check if this looks like a valid address (contains STREET/ST and a borough)
                boroughs = ["MANHATTAN", "BROOKLYN", "QUEENS", "BRONX", "STATEN ISLAND"]
                if any(b in text.upper() for b in boroughs):
                    suggestion.click()
                    wait_for_network_idle(page)
                    print(f"  - Selected address from autocomplete: {text.strip()}")
                    page.wait_for_timeout(3000)  # Wait for map to update and zoom
                    selected_suggestion = True
                    break

            if not selected_suggestion:
                # Fallback: click the first suggestion
                first_suggestion = page.locator(".ui-menu-item, .ui-autocomplete li").first
                if first_suggestion.count() > 0:
                    first_suggestion.click()
                    wait_for_network_idle(page)
                    print("  - Selected first autocomplete suggestion")
                    page.wait_for_timeout(3000)
        except PlaywrightTimeout:
            print("  - No autocomplete suggestions, trying Enter key")
            modal_input.press("Enter")
            wait_for_network_idle(page)
            page.wait_for_timeout(3000)

        # Wait for "Select Address" button to become enabled
        select_btn = page.locator("#SelectAddressMap").first
        expect(select_btn).to_be_visible(timeout=5000)

        # Wait for button to be enabled (not disabled)
        try:
            page.wait_for_function(
                """() => {
                    const btn = document.querySelector('#SelectAddressMap');
                    return btn && !btn.disabled;
                }""",
                timeout=15000
            )
            print("  - Select Address button enabled")
        except PlaywrightTimeout:
            # Save debug info and try alternative approaches
            save_debug_artifacts(page, "address_button_still_disabled")
            print("  - WARNING: Select Address button still disabled")

            # Try clicking on the map canvas to set a pin
            map_canvas = page.locator(".modal canvas, .esri-view-surface canvas").first
            if map_canvas.count() > 0:
                # Click in the center of the map
                box = map_canvas.bounding_box()
                if box:
                    page.mouse.click(box['x'] + box['width'] / 2, box['y'] + box['height'] / 2)
                    wait_for_network_idle(page)
                    print("  - Clicked on map center")
                    page.wait_for_timeout(2000)

        select_btn.click()
        wait_for_network_idle(page)
        print("  - Clicked Select Address")

        # Wait for modal to close
        page.wait_for_timeout(1000)
    except PlaywrightTimeout as e:
        save_debug_artifacts(page, "address_modal_failed")
        # Try to close any open modal by clicking Cancel or X
        cancel_btn = page.locator("#CancelButton, .modal button[data-dismiss='modal'], .modal .close").first
        if cancel_btn.count() > 0:
            try:
                cancel_btn.click(timeout=2000)
                wait_for_network_idle(page)
            except:
                pass
        print(f"  - WARNING: Address search issue: {e}")
        raise  # Re-raise to fail the step properly

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

    # Log what's on the review page
    print("  - Reviewing submission details...")

    if dry_run:
        print("  - DRY RUN: Skipping final submit")
        print("Dry run completed successfully!")
        return True

    # Find and click Submit button (on review page it's "Complete and Submit")
    submit_button = page.get_by_role("button", name="Complete and Submit")
    if submit_button.count() == 0:
        submit_button = page.locator("#NextButton.submit-btn, input[value*='Submit']").first

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

            # Save submission details for notification
            save_submission_details(config, description, nyc_datetime)

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
