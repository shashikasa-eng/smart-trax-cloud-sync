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
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("🔑 Navigating to URL...")
        page.goto(url, wait_until="networkidle", timeout=60000)

        # Login Check
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
            page.wait_for_timeout(8000)

        print("✅ Login completed. Waiting for Dashboard data to load...")
        page.wait_for_timeout(10000)

        # ----------------------------------------------------------------------
        # 🔄 FIX 1: Table Pagination Dropdown ( Rows per page -> 100 / All )
        # ----------------------------------------------------------------------
        try:
            # Dashboard Table එකේ "Rows per page" Dropdown එක තිබේ නම් Maximum කිරීම
            page_select = page.locator(".v-data-table__footer select, select[name*='rows'], div[class*='select']").first
            if page_select.is_visible():
                page_select.select_option(index=-1) # අන්තිම Value එක (100 or All) තෝරයි
                page.wait_for_timeout(3000)
        except Exception as e:
            print(f"ℹ️ Pagination Dropdown Note: {e}")

        # ----------------------------------------------------------------------
        # 📜 FIX 2: Smooth Auto-Scroll (Lazy Loaded / Infinite Scroll Rows ස සඳහා)
        # ----------------------------------------------------------------------
        print("📜 Auto-scrolling to trigger lazy loading...")
        for _ in range(5):
            page.evaluate("window.scrollBy(0, 800)")
            page.wait_for_timeout(1000)
        
        # නැවත Table එක මුලට Scroll කිරීම
        page.evaluate("window.scrollTo(0, 0)")
        page.wait_for_timeout(1000)

        # ----------------------------------------------------------------------
        # 📊 DATA EXTRACTION ENGINE (WITH PAGINATION LOOP)
        # ----------------------------------------------------------------------
        table_data = []
        page_number = 1

        while True:
            print(f"🔍 Extracting rows from Page {page_number}...")
            
            # 1. HTML Tables සෙවීම
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
                    row_vals = [cell.inner_text().strip() for cell in cells]
                    if any(row_vals):
                        # Header එක එක පාරක් විතරක් Table එකට එකතු කිරීම
                        if not table_data or row_vals != table_data[0]:
                            if row_vals not in table_data:
                                table_data.append(row_vals)

            # 2. Div-based Data Grids Fallback
            if not table_data:
                grid_rows = page.locator("div[role='row']:visible, .v-data-table tr:visible").all()
                for row in grid_rows:
                    cells = row.locator("div[role='gridcell'], div[role='columnheader'], td, th").all()
                    row_vals = [cell.inner_text().strip() for cell in cells]
                    if any(row_vals) and row_vals not in table_data:
                        table_data.append(row_vals)

            # ------------------------------------------------------------------
            # ➡️ FIX 3: Check for "NEXT PAGE" Button and Click If Available
            # ------------------------------------------------------------------
            next_button = page.locator("button[aria-label*='Next'], button:has-text('>'), .v-pagination__next button").first
            
            if next_button.is_visible() and next_button.is_enabled():
                print("➡️ Moving to next page...")
                next_button.click()
                page.wait_for_timeout(4000)
                page_number += 1
            else:
                print("✅ Reached the last page of Dashboard data.")
                break

        print(f"📊 Total Extracted Rows across all pages: {len(table_data)}")

        if not table_data:
            print("❌ No main table data found on page!")
            return

        # ----------------------------------------------------------------------
        # 🔄 GOOGLE SHEETS SYNC ENGINE
        # ----------------------------------------------------------------------
        print("🔄 Syncing to Google Sheets...")
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
        print("✅ Google Sheet updated successfully!")

if __name__ == "__main__":
    main()
