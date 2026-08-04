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

    print("🚀 Starting SMART Dashboard Automated Cloud Scraper...")

    with sync_playwright() as p:
        # Browser Launching
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("🔑 Navigating to URL...")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # ----------------------------------------------------------------------
        # 🔐 LOGIN PROCESS
        # ----------------------------------------------------------------------
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

        print("✅ Login completed. Waiting for Dashboard data to load...")
        page.wait_for_timeout(10000)

        # ----------------------------------------------------------------------
        # 🔄 FIX 1: Maximize Rows Per Page Dropdown (If available)
        # ----------------------------------------------------------------------
        try:
            dropdowns = page.locator("select, .v-select, div[class*='rows-per-page']").all()
            for dd in dropdowns:
                if dd.is_visible():
                    dd.click()
                    page.wait_for_timeout(1000)
                    # Option All or 100
                    max_option = page.locator("option, .v-list-item").last
                    if max_option.is_visible():
                        max_option.click()
                        print("⚡ Set Rows Per Page to Maximum!")
                        page.wait_for_timeout(3000)
        except Exception as e:
            print(f"ℹ️ Dropdown handle note: {e}")

        # ----------------------------------------------------------------------
        # 📜 FIX 2: Smooth Scrolling for Lazy Loaded Rows
        # ----------------------------------------------------------------------
        print("📜 Auto-scrolling to capture lazy-loaded users...")
        for _ in range(6):
            page.evaluate("window.scrollBy(0, 1000)")
            page.wait_for_timeout(1000)
        
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # ----------------------------------------------------------------------
        # 📸 DEBUG SCREENSHOT (Web Page එකේ පෙනෙන දේ බලාගැනීමට)
        # ----------------------------------------------------------------------
        page.screenshot(path="smart_dashboard_view.png", full_page=True)
        print("📸 Dashboard View Screenshot captured!")

        # ----------------------------------------------------------------------
        # 📊 FIX 3: Multi-Page Data Extraction Loop
        # ----------------------------------------------------------------------
        table_data = []
        page_count = 1

        while True:
            print(f"🔍 Extracting Table Data from Page {page_count}...")
            
            # Find visible tables
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
                        # Avoid duplicating headers across pages
                        if not table_data or row_vals != table_data[0]:
                            if row_vals not in table_data:
                                table_data.append(row_vals)

            # Fallback for Div-based Data Grids
            if not table_data:
                grid_rows = page.locator("div[role='row']:visible, .v-data-table tr:visible").all()
                for row in grid_rows:
                    cells = row.locator("div[role='gridcell'], div[role='columnheader'], td, th").all()
                    row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]
                    if any(row_vals) and row_vals not in table_data:
                        table_data.append(row_vals)

            # ➡️ Check for Next Page Button
            next_btn = page.locator("button[aria-label*='Next'], button:has-text('>'), .v-pagination__next button, li.next:not(.disabled) a").first
            
            if next_btn.is_visible() and next_btn.is_enabled():
                print(f"➡️ Clicking Next Page (Moving to Page {page_count + 1})...")
                next_btn.click()
                page.wait_for_timeout(4000)
                page_count += 1
            else:
                print("✅ All pages scraped successfully!")
                break

        print(f"📊 Total Rows Extracted across all pages: {len(table_data)}")

        if not table_data:
            print("❌ No table data found on the dashboard page!")
            return

        # ----------------------------------------------------------------------
        # 🔄 GOOGLE SHEETS SYNC
        # ----------------------------------------------------------------------
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
        print("🎉 SUCCESS: Google Sheet 'QAT Raw Data' updated perfectly!")

if __name__ == "__main__":
    main()
