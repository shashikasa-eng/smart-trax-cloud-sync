import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def get_env_variable(var_name: str) -> str:
    val = os.environ.get(var_name)
    if not val:
        raise ValueError(f"Missing environment variable: {var_name}")
    return val

def main():
    logging.info("🚀 Starting Ultra-Fast Fast-Inject PowerBI Scraper...")

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
            page.goto(url, wait_until="domcontentloaded", timeout=45000)

            # Fast Login
            if "login" in page.url.lower() or page.locator("input[type='password']").count() > 0:
                logging.info("🔐 Logging in...")
                if page.locator("input[type='email']").count() > 0:
                    page.fill("input[type='email']", username)
                elif page.locator("input[name='username']").count() > 0:
                    page.fill("input[name='username']", username)
                else:
                    page.fill("input[type='text']", username)

                page.fill("input[type='password']", password)
                page.keyboard.press("Enter")
                page.wait_for_timeout(7000)

            logging.info("✅ Login Done. Waiting for visual grid...")
            page.wait_for_timeout(8000)

            # ----------------------------------------------------------------------
            # ⚡ ULTRA-FAST DIRECT JAVASCRIPT TABLE EXTRACTION ENGINE
            # ----------------------------------------------------------------------
            logging.info("⚡ Executing In-Memory JavaScript DOM Scraper & Fast Scroll...")

            extracted_rows_dict = {}

            # Fast 10-Step JS Inner Scroll & Data Collector
            for step in range(10):
                # JS Script: Read all visible rows directly from DOM/iFrames
                raw_extracted_rows = page.evaluate("""
                    () => {
                        const results = [];
                        // Search all elements matching rows or table rows across main DOM & frames
                        const rowElements = document.querySelectorAll('tr, div[role="row"]');
                        
                        rowElements.forEach(row => {
                            const cells = row.querySelectorAll('td, th, div[role="gridcell"]');
                            const cellVals = Array.from(cells).map(c => c.innerText.trim().replace(/\\n/g, ' ')).filter(v => v !== '');
                            if (cellVals.length > 1) {
                                results.push(cellVals);
                            }
                        });

                        // Scroll all containers down
                        const containers = document.querySelectorAll('div, section, main');
                        containers.forEach(c => {
                            if (c.scrollHeight > c.clientHeight) {
                                c.scrollTop += 900;
                            }
                        });
                        window.scrollBy(0, 900);

                        return results;
                    }
                """)

                # Clean & Store Unique Rows
                for row_vals in raw_extracted_rows:
                    if row_vals and len(row_vals) >= 2:
                        first_col = str(row_vals[0]).strip().upper()
                        # Pick rows starting with K or Headers
                        if first_col.startswith("K") or "QAT" in first_col:
                            unique_key = " | ".join(row_vals[:4])
                            if unique_key not in extracted_rows_dict:
                                extracted_rows_dict[unique_key] = row_vals

                page.wait_for_timeout(800)

            table_data = list(extracted_rows_dict.values())

            # Header Fallback
            if not table_data or not any("QAT" in str(cell).upper() for cell in table_data[0]):
                headers = ["QAT ID", "QAT Name", "Project", "Trax Category G1", "Trax Category G2", "Task Type", "Task ID", "Task Duration", "QAT Status", "Status Duration", "Last Login Time", "Start Shift Time"]
                table_data.insert(0, headers)

            # ----------------------------------------------------------------------
            # 📋 ENTERPRISE DIAGNOSTIC PRINT LOG
            # ----------------------------------------------------------------------
            print("\n==================================================")
            print("📊 --- COMPLETE DASHBOARD SCRAPED LOG ---")
            print("==================================================")
            print(f"📊 Total Extracted Dynamic Rows (including headers): {len(table_data)}")

            extracted_qids = set()
            for r in table_data:
                if r and len(r) > 0 and str(r[0]).strip().upper().startswith("K"):
                    extracted_qids.add(str(r[0]).strip().upper())

            print(f"✅ Total Unique QAT IDs Captured: {len(extracted_qids)}")
            print(f"📌 Found QIDs List: {sorted(list(extracted_qids))}")
            print("--------------------------------------------------")

            for idx, row in enumerate(table_data):
                print(f"Row {idx+1}: {row}")
            print("==================================================\n")

            if len(table_data) <= 1:
                logging.error("❌ Extraction Failed: No rows captured!")
                return

            # ----------------------------------------------------------------------
            # 🔄 GOOGLE SHEETS PIPELINE
            # ----------------------------------------------------------------------
            logging.info("🔄 Syncing Extracted Data to Google Sheets...")
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

        except Exception as ex:
            logging.error(f"❌ Error during execution: {ex}")
            raise ex
        finally:
            browser.close()

if __name__ == "__main__":
    main()
