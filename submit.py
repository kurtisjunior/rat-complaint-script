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

from playwright.sync_api import (
    sync_playwright,
    expect,
    TimeoutError as PlaywrightTimeout,
)


# Constants
FORM_DIRECT_URL = "https://portal.311.nyc.gov/sr-step/?id=fb797007-e3f3-f011-92b8-7c1e52e6db72&stepid=4a51f5a5-b04c-e811-a835-000d3a33b1e4"
# Main Rat or Mouse Complaint article page (fallback)
FORM_ARTICLE_URL = "https://portal.311.nyc.gov/article/?kanumber=KA-01107"

DESCRIPTIONS = [
    "This is getting worse and has become a health hazard. It is a loop: open food and trash attracts rats, rats spread more contamination, and then even more rats appear. Management is doing nothing to break that cycle. The neglect is disgusting and unacceptable; please inspect and enforce correction immediately.",
    "Rat activity is increasing week after week, including daytime sightings on the sidewalk. Trash is left open with no secure bins or tight lids, so food is always available. This is not self-correcting; it keeps feeding a worsening rat loop. Total management neglect is making conditions disgusting and unacceptable.",
    "This infestation keeps escalating because garbage is exposed every day. The pattern is clear: food and open trash bring rats, and more rats make the situation worse. There are still no consistently covered bins and no meaningful action from management. Please issue violations and require immediate abatement.",
    "I now see more rats than before, often in daylight where people walk. Open trash and no proper lidded containers are creating continuous attractants. This is a serious sanitation and health hazard that will only worsen without enforcement. Management has neglected this for too long and conditions are unacceptable.",
    "This is no longer occasional rodent activity; it is a worsening cycle. Food waste sits exposed, rats feed and multiply, and the next day there are even more rats. The building still does not maintain covered, rodent-resistant bins. The ongoing neglect by management is disgusting and requires enforcement.",
    "The rat problem is clearly getting worse over time. Trash is routinely open, bins are not properly covered, and rats are visible in daytime near pedestrian paths. That food-rat loop is active every day and nothing meaningful is being done to stop it. Please inspect now and compel immediate corrective action.",
    "These conditions are a public health hazard and are deteriorating. Open garbage, no tight-fitting lids, and no sustained management response are fueling increased rat activity. This is exactly the kind of recurring attractant condition that keeps infestations growing. The neglect is unacceptable; please enforce abatement.",
    "I continue to observe rising rat sightings linked to exposed refuse and poor trash control. The cycle is constant: accessible food leads to more rats, and more rats worsen the contamination. Management has failed to provide or maintain proper covered bins. This ongoing neglect is disgusting and must be corrected.",
    "Rats are active in daylight and the infestation is worsening, not improving. Garbage remains uncovered and unsecured, with no consistent use of tight-lid containers. Without intervention, this loop will continue to produce more rats and greater health risk. Please inspect and issue immediate corrective orders.",
    "This property shows chronic conditions that attract rodents and now escalating daytime rat traffic. Open trash and lack of compliant covered bins are the direct drivers. Management has taken no effective action, and the result is a worsening, unsanitary cycle. Conditions are unacceptable and require urgent enforcement.",
    "The situation is getting worse because trash is always open and accessible. It is a feedback loop: food attracts rats, rats multiply, and each week there are more sightings. There is still no adequate covered container system in place. This level of neglect is disgusting and poses a serious health concern.",
    "There are visibly more rats now than in prior months, with activity during the day. Exposed garbage and missing or uncovered bins are allowing continuous feeding and breeding. Management inaction has turned this into an ongoing worsening hazard. Please document violations, mandate covered containers, and reinspect.",
]

ADDITIONAL_DETAILS = "Trash, Improper garbage storage or disposal, Open lot"

# Default address (can be overridden via environment variables)
DEFAULT_ADDRESS = "932 Carroll St"
DEFAULT_CITY = "Brooklyn"
DEFAULT_STATE = "NY"
DEFAULT_ZIP = "11225"
DEFAULT_CONTACT_FIRST_NAME = "Kurtis"
DEFAULT_CONTACT_LAST_NAME = "Angell"
DEFAULT_CONTACT_EMAIL = "kurtisangell@gmail.com"
DEFAULT_CONTACT_ADDRESS_LINE1 = "932 Carroll ST APT 1F"
DEFAULT_CONTACT_ADDRESS_LINE2 = ""
DEFAULT_CONTACT_CITY = "New York"
DEFAULT_CONTACT_STATE = "NY"
DEFAULT_CONTACT_ZIP = "11225"
DEFAULT_CONTACT_COUNTRY = "United States"


def normalize_us_zip(zip_code):
    """Normalize ZIP code to first 5 digits when possible."""
    digits = "".join(ch for ch in zip_code if ch.isdigit())
    if len(digits) >= 5:
        return digits[:5]
    return zip_code.strip()


def get_config():
    """Get configuration from environment variables with defaults."""
    return {
        "address": os.environ.get("ADDRESS", DEFAULT_ADDRESS),
        "city": os.environ.get("CITY", DEFAULT_CITY),
        "state": os.environ.get("STATE", DEFAULT_STATE),
        "zip": os.environ.get("ZIP", DEFAULT_ZIP),
        "contact_first_name": os.environ.get(
            "CONTACT_FIRST_NAME", DEFAULT_CONTACT_FIRST_NAME
        ),
        "contact_last_name": os.environ.get(
            "CONTACT_LAST_NAME", DEFAULT_CONTACT_LAST_NAME
        ),
        "contact_email": os.environ.get("CONTACT_EMAIL", DEFAULT_CONTACT_EMAIL),
        "contact_address_line1": os.environ.get(
            "CONTACT_ADDRESS_LINE1", DEFAULT_CONTACT_ADDRESS_LINE1
        ),
        "contact_address_line2": os.environ.get(
            "CONTACT_ADDRESS_LINE2", DEFAULT_CONTACT_ADDRESS_LINE2
        ),
        "contact_city": os.environ.get("CONTACT_CITY", DEFAULT_CONTACT_CITY),
        "contact_state": os.environ.get("CONTACT_STATE", DEFAULT_CONTACT_STATE),
        "contact_zip": normalize_us_zip(
            os.environ.get("CONTACT_ZIP", DEFAULT_CONTACT_ZIP)
        ),
        "contact_country": os.environ.get("CONTACT_COUNTRY", DEFAULT_CONTACT_COUNTRY),
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

    details = f"""Address: {config["address"]}, {config["city"]}, {config["state"]} {config["zip"]}
Location Type: 3+ Family Apt. Building
Problem Detail: Condition Attracting Rodents
Additional Details: Garbage
Date/Time Observed: {nyc_datetime.strftime("%-m/%-d/%Y %-I:%M %p")}
Recurring: Yes
Contact Name: {config["contact_first_name"]} {config["contact_last_name"]}
Contact Email: {config["contact_email"]}
Contact Address: {config["contact_address_line1"]}, {config["contact_city"]}, {config["contact_state"]} {config["contact_zip"]}

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
                    if box and box["width"] > 50 and box["height"] > 50:
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
        active = page.locator(
            f".progress-step.active:has-text('{step}'), [aria-current='step']:has-text('{step}')"
        ).first
        if active.count() > 0:
            return step
    # Fallback: check for step-specific elements
    if page.locator("#n311_problemdetailid_select").count() > 0:
        return 1
    if page.locator("#n311_locationtypeid_select").count() > 0:
        return 2
    if (
        page.locator(
            "fieldset[aria-label*='Contact'], input[id*='firstname']"
        ).first.count()
        > 0
    ):
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
            save_debug_artifacts(
                page, f"step_transition_failed_expected_{expected_next_step}"
            )
            raise Exception(
                f"Step transition failed: expected step {expected_next_step}, got {current}"
            )


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
    report_button = page.locator(
        "a:has-text('Report rats or conditions that might attract them')"
    ).first
    if report_button.count() == 0:
        # Try alternative - look for any DOHMH rat report button in expanded section
        report_button = page.locator("a.btn:has-text('Report rats')").first
    if report_button.count() == 0:
        report_button = page.locator(
            "a[onclick*='createServiceRequest']:has-text('Report rats')"
        ).first

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
    additional_details = page.locator(
        "select[id*='additionaldetails'], select[id*='additional']"
    ).first
    try:
        additional_details.wait_for(state="visible", timeout=5000)
    except PlaywrightTimeout:
        additional_details = None

    if (
        additional_details
        and additional_details.count() > 0
        and additional_details.is_visible()
    ):
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
                additional_details.select_option(
                    label=additional_details.locator(
                        f"option:has-text('{pref}')"
                    ).first.text_content()
                )
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
    datetime_field = page.locator(
        "input[id='n311_datetimeobserved']:visible, input[placeholder*='M/D/YYYY']:visible"
    ).first
    if datetime_field.count() > 0:
        expect(datetime_field).to_be_visible(timeout=5000)
        datetime_field.click()
        datetime_field.fill(datetime_str)
        # Press Tab to close any date picker that might open
        datetime_field.press("Tab")
        print(f"  - Set Date/Time Observed: {datetime_str}")

    # Select "Yes" for recurring problem
    recurring_group = page.locator(
        "fieldset:has-text('recurring'), div:has-text('recurring')"
    ).first
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
        timeout=15000,
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
                timeout=10000,
            )
            # Try to select appropriate option for building exterior
            detail_options = [
                "Exterior",
                "Outside",
                "Sidewalk",
                "Street",
                "Front",
                "Building",
            ]
            selected = False
            for opt in detail_options:
                if location_detail.locator(f"option:has-text('{opt}')").count() > 0:
                    location_detail.select_option(
                        label=location_detail.locator(
                            f"option:has-text('{opt}')"
                        ).first.text_content()
                    )
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
        address_text = config["address"]
        modal_input.type(
            address_text, delay=100
        )  # Type with delay to trigger autocomplete
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
                first_suggestion = page.locator(
                    ".ui-menu-item, .ui-autocomplete li"
                ).first
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
                timeout=15000,
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
                    page.mouse.click(
                        box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
                    )
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
        cancel_btn = page.locator(
            "#CancelButton, .modal button[data-dismiss='modal'], .modal .close"
        ).first
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


def fill_step3_who(page, config):
    """Step 3: Fill contact information."""
    print("Step 3: Filling contact info...")

    wait_for_network_idle(page)

    def fill_visible_field(field_name, selectors, value):
        """Fill the first visible matching field."""
        if not value:
            return False

        for selector in selectors:
            locator = page.locator(selector)
            count = locator.count()
            for i in range(count):
                candidate = locator.nth(i)
                try:
                    if candidate.is_visible():
                        candidate.fill(value)
                        print(f"  - Filled {field_name}: {value}")
                        return True
                except Exception:
                    continue
        return False

    fill_visible_field(
        "Contact First Name",
        [
            "input#n311_portaldobcontactfirstname:visible",
            "input[id*='contactfirstname']:visible",
            "input[id*='firstname']:visible",
        ],
        config["contact_first_name"],
    )
    fill_visible_field(
        "Contact Last Name",
        [
            "input#n311_portaldobcontactlastname:visible",
            "input[id*='contactlastname']:visible",
            "input[id*='lastname']:visible",
        ],
        config["contact_last_name"],
    )
    fill_visible_field(
        "Contact Email",
        [
            "input#n311_contactemail:visible",
            "input[id*='contactemail']:visible",
            "input[type='email']:visible",
            "input[id*='email']:visible",
        ],
        config["contact_email"],
    )
    fill_visible_field(
        "Contact Address Line 1",
        [
            "input#n311_portalcustomeraddressline1:visible",
            "input[id*='addressline1']:visible",
        ],
        config["contact_address_line1"],
    )
    if config["contact_address_line2"]:
        fill_visible_field(
            "Contact Address Line 2",
            [
                "input#n311_portalcustomeraddressline2:visible",
                "input[id*='addressline2']:visible",
            ],
            config["contact_address_line2"],
        )
    fill_visible_field(
        "Contact City",
        [
            "input#n311_portalcustomeraddresscity:visible",
            "input[id*='addresscity']:visible",
            "input[id*='city']:visible",
        ],
        config["contact_city"],
    )
    fill_visible_field(
        "Contact State",
        [
            "input#n311_portalcustomeraddressstate:visible",
            "input[id*='addressstate']:visible",
            "input[id*='state']:visible",
        ],
        config["contact_state"],
    )
    fill_visible_field(
        "Contact ZIP",
        [
            "input#n311_portalcustomeraddresszip:visible",
            "input[id*='addresszip']:visible",
            "input[id*='zip']:visible",
            "input[id*='postal']:visible",
        ],
        config["contact_zip"],
    )
    # Country is optional on many forms; fill when an input exists.
    fill_visible_field(
        "Contact Country",
        [
            "input[id*='country']:visible",
        ],
        config["contact_country"],
    )

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
        submit_button = page.locator(
            "#NextButton.submit-btn, input[value*='Submit']"
        ).first

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
        if (
            "thank you" in page_text
            or "confirmation" in page_text
            or "submitted" in page_text
        ):
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
    print(
        f"Address: {config['address']}, {config['city']}, {config['state']} {config['zip']}"
    )
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
            fill_step3_who(page, config)
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
