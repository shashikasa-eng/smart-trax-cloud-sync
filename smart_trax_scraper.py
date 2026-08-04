import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def get_env_variable(var_name: str) -> str:
    val = os.environ.get(var_name)
    if not val:
        logging.error(f"❌ Missing environment variable: {var_name}")
        raise ValueError(f"Missing environment variable: {var_name}")
    return val

def main():
    logging.info("🚀 Starting PowerBI Ultra-Precision Keyboard & Grid Focused Scraper...")

    url = get_env_variable("SMART_URL")
    username = get_env_variable("SMART_USERNAME")
    password = get_env_variable("SMART_PASSWORD")
    sheet_name = get_env_variable("SHEET_NAME")
    creds_json = get_env_variable("GOOGLE_CREDS_JSON")

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        try:
            logging.info("🔑 Navigating to SMART Trax Dashboard...")
            page.goto(url, wait_until="domcontentloaded", timeout=60000)

            # Login Handling
            if "login" in page.url.lower() or page.locator("input[type='password']").count() > 0:
                logging.info("🔐 Logging into SMART Trax Cloud Portal...")
                if page.locator("input[type='email']").count() > 0:
                    page.fill("input[type='email']", username)
                elif page.locator("input[name='username']").count() > 0:
                    page.fill("input[name='username']", username)
                else:
                    page.fill("input[type='text']", username)

                page.fill("input[type='password']", password)
                page.keyboard.press("Enter")
                page.wait_for_timeout(10000)

            logging.info("✅ Login successful. Waiting for PowerBI Table to render...")
            page.wait_for_timeout(12000)

            # ----------------------------------------------------------------------
            # 📜 POWERBI KEYBOARD & GRID SCROLLING ENGINE
            # ----------------------------------------------------------------------
            table_data = []
            seen_rows = set()

            # 1. Extract Column Headers
            header_cells = page.locator("th, div[role='columnheader']").all()
            if header_cells:
                headers = [h.inner_text().strip().replace('\n', ' ') for h in header_cells if h.inner_text().strip()]
                if headers:
                    table_data.append(headers)

            # 2. Focus on PowerBI Table Grid
            grid_element = page.locator("div[role='grid'], table, .v-data-table").first
            if grid_element.is_visible():
                grid_element.click()
                page.wait_for_timeout(1000)

            # 3. Step-by-Step Deep Keyboard Scrolling
            logging.info("📜 Executing Key-Press Scrolling to reach the very bottom (including K20896 & beyond)...")

            for scroll_step in range(25):
                # Fetch currently rendered rows
                rows = page.locator("tr, div[role='row']").all()
                for row in rows:
                    cells = row.locator("td, th, div[role='gridcell']").all()
                    row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]

                    if any(row_vals) and len(row_vals) > 2:
                        # Row unique identifier to prevent exact duplicates
                        row_key = " | ".join(row_vals)
                        if row_key not in seen_rows:
                            seen_rows.add(row_key)
                            table_data.append(row_vals)

                # Simulate Keyboard PageDown and ArrowDown to force PowerBI DOM update
                page.keyboard.press("PageDown")
                page.wait_for_timeout(800)
                
                # Mouse Wheel Fallback inside container
                page.mouse.wheel(0, 1000)
                page.wait_for_timeout(500)

            # ----------------------------------------------------------------------
            # 📋 ENTERPRISE DIAGNOSTIC LOG ENGINE
            # ----------------------------------------------------------------------
            print("\n==================================================")
            print("📊 --- COMPLETE DASHBOARD SCRAPED LOG ---")
            print("==================================================")
            print(f"📊 Total Extracted Dynamic Rows (including headers): {len(table_data)}")

            extracted_qids = set()
            for r in table_data[1:]:
                if r and len(r) > 0 and (r[0].strip().startswith("K") or r[0].strip().startswith("k")):
                    extracted_qids.add(r[0].strip().upper())

            print(f"✅ Total Unique QAT IDs Captured: {len(extracted_qids)}")
            print(f"📌 Found QIDs List: {sorted(list(extracted_qids))}")
            print("--------------------------------------------------")

            for idx, row in enumerate(table_data):
                print(f"Row {idx+1}: {row}")
            print("==================================================\n")

            if not table_data:
                logging.error("❌ Extraction Failed: No data rows captured from Dashboard!")
                return

            # ----------------------------------------------------------------------
            # 🔄 GOOGLE SHEETS PIPELINE
            # ----------------------------------------------------------------------
            logging.info("🔄 Syncing Extracted Data to Google Sheets API...")
            creds_dict = json.loads(creds_json)
            scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
            creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
            client = gspread.authorize(creds)

            spreadsheet = client.open(sheet_name)
            try:
                worksheet = spreadsheet.worksheet("QAT Raw Data")
            except Exception:
                worksheet = spreadsheet.get_worksheet(0)

            worksheet.clear()
            worksheet.update('A1', table_data)
            logging.info("🎉 SUCCESS: Entire PowerBI Dashboard Data updated to Google Sheet!")

        except PlaywrightTimeoutError as e:
            logging.error(f"❌ Timeout Exception: {e}")
            raise e
        except Exception as ex:
            logging.error(f"❌ Unexpected Error: {ex}")
            raise ex
        finally:
            browser.close()

if __name__ == "__main__":
    main()
