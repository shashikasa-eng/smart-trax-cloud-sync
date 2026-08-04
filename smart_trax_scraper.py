import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

def main():
    url = os.environ.get("SMART_URL")
    username = os.environ.get("SMART_USERNAME")
    password = os.environ.get("SMART_PASSWORD")
    sheet_name = os.environ.get("SHEET_NAME")
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")

    if not all([url, username, password, sheet_name, creds_json]):
        raise Exception("Missing required environment variables in GitHub Secrets!")

    print("🚀 Starting Dynamic SMART Scraper...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("🔑 Navigating to URL...")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Login Handling
        if "login" in page.url.lower() or page.locator("input[type='password']").count() > 0:
            print("🔐 Logging into SMART Trax Cloud...")
            if page.locator("input[type='email']").count() > 0:
                page.fill("input[type='email']", username)
            elif page.locator("input[name='username']").count() > 0:
                page.fill("input[name='username']", username)
            else:
                page.fill("input[type='text']", username)

            page.fill("input[type='password']", password)
            page.keyboard.press("Enter")
            page.wait_for_timeout(10000)

        print("✅ Login completed. Loading full dataset...")
        page.wait_for_timeout(10000)

        # Dropdowns Reset
        try:
            select_elements = page.locator("select, .v-select, div[class*='rows-per-page'], div[class*='pagination']").all()
            for elem in select_elements:
                if elem.is_visible():
                    elem.click()
                    page.wait_for_timeout(1000)
                    last_opt = page.locator("option, .v-list-item").last
                    if last_opt.is_visible():
                        last_opt.click()
                        print("⚡ Set Table View to MAXIMUM ROWS!")
                        page.wait_for_timeout(2000)
        except Exception as e:
            print(f"ℹ️ Filter handling note: {e}")

        # Infinite Scroll
        print("📜 Auto-scrolling page to trigger dynamic database loading...")
        previous_height = 0
        for _ in range(10):
            page.evaluate("window.scrollBy(0, 1200)")
            page.wait_for_timeout(1000)
            current_height = page.evaluate("document.body.scrollHeight")
            if current_height == previous_height:
                break
            previous_height = current_height

        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # Extraction Engine
        table_data = []
        page_num = 1

        while True:
            print(f"🔍 Extracting raw records from Dynamic Page {page_num}...")
            tables = page.locator("table:visible").all()
            best_table_rows = []

            if tables:
                max_rows = 0
                for t in tables:
                    rows = t.locator("tr").all()
                    if len(rows) > max_rows:
                        max_rows = len(rows)
                        best_table_rows = rows

                for row in best_table_rows:
                    cells = row.locator("th, td").all()
                    row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]
                    if any(row_vals):
                        if not table_data or row_vals != table_data[0]:
                            if row_vals not in table_data:
                                table_data.append(row_vals)

            if not table_data:
                grid_rows = page.locator("div[role='row']:visible, .v-data-table tr:visible").all()
                for row in grid_rows:
                    cells = row.locator("div[role='gridcell'], div[role='columnheader'], td, th").all()
                    row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]
                    if any(row_vals) and row_vals not in table_data:
                        table_data.append(row_vals)

            next_btn = page.locator("button[aria-label*='Next'], button:has-text('>'), .v-pagination__next button, li.next:not(.disabled) a").first
            if next_btn.is_visible() and next_btn.is_enabled():
                print(f"➡️ Dynamic pagination detected. Moving to Page {page_num + 1}...")
                next_btn.click()
                page.wait_for_timeout(4000)
                page_num += 1
            else:
                print("✅ All dynamic pages successfully fetched!")
                break

        print(f"📊 TOTAL RECORDS EXTRACTED: {len(table_data)}")

        if not table_data:
            print("❌ No dynamic table data found!")
            return

        # Google Sheet Sync
        print("🔄 Syncing Extracted Data to Google Sheets...")
        creds_dict = json.loads(creds_json)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)

        spreadsheet = client.open(sheet_name)
        try:
            worksheet = spreadsheet.worksheet("QAT Raw Data")
        except:
            worksheet = spreadsheet.get_worksheet(0)

        worksheet.clear()
        worksheet.update('A1', table_data)
        print("🎉 SUCCESS: Raw Data Sheet updated dynamically!")

if __name__ == "__main__":
    main()
