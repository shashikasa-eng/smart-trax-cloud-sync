import os
import json
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeoutError

# Configure Enterprise-grade Logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler()]
)

def get_env_variable(var_name: str) -> str:
    """Retrieve environment variables safely."""
    val = os.environ.get(var_name)
    if not val:
        logging.error(f"❌ Critical Error: Missing required environment variable '{var_name}'")
        raise ValueError(f"Missing required environment variable: {var_name}")
    return val

def main():
    logging.info("🚀 Initializing Production Scraper Engine v4.0 (JS-Injected Virtual DOM Engine)...")

    # Load and validate environment variables
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

            # Authentication Handling Engine
            if "login" in page.url.lower() or page.locator("input[type='password']").count() > 0:
                logging.info("🔐 Logging into SMART Trax Cloud Portal...")
                
                # Email/Username Field Auto-Detection
                if page.locator("input[type='email']").count() > 0:
                    page.fill("input[type='email']", username)
                elif page.locator("input[name='username']").count() > 0:
                    page.fill("input[name='username']", username)
                else:
                    page.fill("input[type='text']", username)

                page.fill("input[type='password']", password)
                page.keyboard.press("Enter")
                page.wait_for_timeout(10000)

            logging.info("✅ Authentication Successful. Waiting for PowerBI / DataGrid render...")
            page.wait_for_timeout(10000)

            # ----------------------------------------------------------------------
            # 📜 ADVANCED VIRTUAL DOM INNER SCROLLING ENGINE
            # ----------------------------------------------------------------------
            logging.info("📜 Executing Deep JavaScript DOM Scroll Trigger...")

            table_data = []

            # Extract Column Headers
            header_cells = page.locator("th, div[role='columnheader']").all()
            if header_cells:
                headers = [h.inner_text().strip().replace('\n', ' ') for h in header_cells if h.inner_text().strip()]
                if headers:
                    table_data.append(headers)

            # Iterative Multi-Level DOM Scroll
            for step in range(20):
                # JS Injection to force scroll all inner scrollable containers
                page.evaluate("""
                    () => {
                        const scrollables = document.querySelectorAll('div, section, main, table, [role="grid"]');
                        scrollables.forEach(el => {
                            if (el.scrollHeight > el.clientHeight) {
                                el.scrollTop += 800;
                            }
                        });
                        window.scrollBy(0, 800);
                    }
                """)
                page.wait_for_timeout(1000)

                # Capture currently visible grid cells/rows
                rows = page.locator("tr, div[role='row']").all()
                for row in rows:
                    cells = row.locator("td, th, div[role='gridcell']").all()
                    row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]

                    # Row validation & De-duplication
                    if any(row_vals) and len(row_vals) > 2:
                        if row_vals not in table_data:
                            table_data.append(row_vals)

            # ----------------------------------------------------------------------
            # 📋 ENTERPRISE DIAGNOSTIC PRINT LOG ENGINE
            # ----------------------------------------------------------------------
            print("\n==================================================")
            print("📊 --- COMPLETE DASHBOARD SCRAPED LOG ---")
            print("==================================================")
            print(f"📊 Total Extracted Dynamic Rows (including headers): {len(table_data)}")

            extracted_qids = set()
            for r in table_data[1:]:
                if r and len(r) > 0 and r[0].strip().startswith("K"):
                    extracted_qids.add(r[0].strip())

            print(f"✅ Total Dynamic QAT IDs Captured: {len(extracted_qids)}")
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
            logging.info("🎉 SUCCESS: Company Project Scraper completed successfully!")

        except PlaywrightTimeoutError as e:
            logging.error(f"❌ Timeout Exception during Scraper execution: {e}")
            raise e
        except Exception as ex:
            logging.error(f"❌ Unexpected Error occurred: {ex}")
            raise ex
        finally:
            browser.close()

if __name__ == "__main__":
    main()
