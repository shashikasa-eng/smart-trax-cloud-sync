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
    logging.info("🚀 Starting Universal Smart Dashboard Scraper (DOM Target Engine)...")

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

            logging.info("✅ Login successful. Waiting for Dashboard Visuals to load...")
            page.wait_for_timeout(12000)

            # ----------------------------------------------------------------------
            # 📜 UNIVERSAL DOM EXTRACTION ENGINE WITH JS SCROLL
            # ----------------------------------------------------------------------
            table_data = []
            extracted_rows_dict = {}

            # Step 1: Capture Headers
            header_cells = page.locator("th, div[role='columnheader']").all()
            headers = []
            if header_cells:
                headers = [h.inner_text().strip().replace('\n', ' ') for h in header_cells if h.inner_text().strip()]
            
            if not headers:
                # Default Headers if PowerBI hides header elements
                headers = ["QAT ID", "QAT Name", "Project", "Trax Category G1", "Trax Category G2", "Task Type", "Task ID", "Task Duration", "QAT Status", "Status Duration", "Last Login Time", "Start Shift Time"]

            table_data.append(headers)

            # Step 2: Multi-Pass JS Scroll & Element Scan
            logging.info("📜 Scanning Dashboard Elements and Scrolling Inner Containers...")

            for pass_num in range(15):
                # JS Injection to force scroll all scrollable elements
                page.evaluate("""
                    () => {
                        const containers = document.querySelectorAll('div, section, main, iframe');
                        containers.forEach(c => {
                            if (c.scrollHeight > c.clientHeight) {
                                c.scrollTop += 700;
                            }
                        });
                        window.scrollBy(0, 700);
                    }
                """)
                page.wait_for_timeout(1200)

                # Scan all rows in DOM
                rows = page.locator("tr, div[role='row'], div[class*='row']").all()
                for r in rows:
                    try:
                        cells = r.locator("td, th, div[role='gridcell'], div[class*='cell']").all()
                        row_vals = [c.inner_text().strip().replace('\n', ' ') for c in cells if c.inner_text().strip() != ""]

                        # Check if row has data and contains a valid QAT ID (Starts with K or k)
                        if row_vals and len(row_vals) >= 2:
                            first_col = row_vals[0].upper()
                            if first_col.startswith("K"):
                                # Unique Key combination (QAT ID + Task ID if present) to avoid duplicates
                                unique_key = " | ".join(row_vals[:3])
                                if unique_key not in extracted_rows_dict:
                                    extracted_rows_dict[unique_key] = row_vals
                    except Exception:
                        continue

            # Append all cleaned unique rows
            for row in extracted_rows_dict.values():
                table_data.append(row)

            # ----------------------------------------------------------------------
            # 📋 DIAGNOSTIC LOG ENGINE
            # ----------------------------------------------------------------------
            print("\n==================================================")
            print("📊 --- COMPLETE DASHBOARD SCRAPED LOG ---")
            print("==================================================")
            print(f"📊 Total Extracted Dynamic Rows (including headers): {len(table_data)}")

            extracted_qids = set()
            for r in table_data[1:]:
                if r and len(r) > 0 and r[0].strip().upper().startswith("K"):
                    extracted_qids.add(r[0].strip().upper())

            print(f"✅ Total Unique QAT IDs Captured: {len(extracted_qids)}")
            print(f"📌 Found QIDs List: {sorted(list(extracted_qids))}")
            print("--------------------------------------------------")

            for idx, row in enumerate(table_data):
                print(f"Row {idx+1}: {row}")
            print("==================================================\n")

            if len(table_data) <= 1:
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
