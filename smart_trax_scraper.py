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

    print("🚀 Starting Complete Universal Dashboard Scraper (Full Dynamic Engine)...")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={'width': 1920, 'height': 1080})
        page = context.new_page()

        print("🔑 Navigating to SMART Dashboard URL...")
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

        print("✅ Login completed. Waiting for Dashboard PowerBI/DataGrid elements to populate...")
        page.wait_for_timeout(12000)

        # ----------------------------------------------------------------------
        # 📜 INNER TABLE VIRTUAL SCROLLING ENGINE (All Rows Capture)
        # ----------------------------------------------------------------------
        print("📜 Activating Inner Table Virtual Scrollbar to load ALL QAT Rows...")

        table_data = []
        
        # PowerBI / Grid Containers & Tables detection
        grid_selector = "div[role='grid'], .v-data-table, table, div[class*='scroll']"
        
        # Get Column Headers
        header_cells = page.locator("th, div[role='columnheader']").all()
        if header_cells:
            headers = [h.inner_text().strip().replace('\n', ' ') for h in header_cells if h.inner_text().strip()]
            if headers and headers not in table_data:
                table_data.append(headers)

        # Inner Scroll loop to trigger virtual row rendering
        scroll_container = page.locator(grid_selector).first
        
        previous_row_count = 0
        scroll_attempts = 0
        max_attempts = 35  # Continuous inner scrolling

        while scroll_attempts < max_attempts:
            # Table එකේ පේන සෑම Row එකක්ම Scan කර ගැනීම
            rows = page.locator("tr, div[role='row']").all()
            
            for row in rows:
                cells = row.locator("td, th, div[role='gridcell']").all()
                row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]
                
                # Non-empty dynamic row validation
                if any(row_vals) and len(row_vals) > 2:
                    if row_vals not in table_data:
                        table_data.append(row_vals)

            # Inner Container එක පල්ලෙහාට Scroll කිරීම (Mouse Wheel & JavaScript)
            if scroll_container.is_visible():
                scroll_container.hover()
                page.mouse.wheel(0, 1500)
            else:
                page.evaluate("window.scrollBy(0, 1000)")

            page.wait_for_timeout(1200)

            # Check if new rows were added
            current_row_count = len(table_data)
            if current_row_count == previous_row_count:
                scroll_attempts += 1
            else:
                scroll_attempts = 0  # Reset if new rows found
                previous_row_count = current_row_count

        # ----------------------------------------------------------------------
        # 📋 FULL DIAGNOSTIC PRINT LOG (GitHub Console එකේ බලාගැනීමට)
        # ----------------------------------------------------------------------
        print("\n==================================================")
        print("📊 --- SCRAPED SUMMARY & PREVIEW LOG ---")
        print("==================================================")
        print(f"📊 Total Extracted Dynamic Rows (including header): {len(table_data)}")
        
        # Extracted QAT IDs ටික වෙනම Print කර පෙන්වීම
        extracted_qids = set()
        for r in table_data[1:]:
            if r and len(r) > 0 and r[0].strip().startswith("K"):
                extracted_qids.add(r[0].strip())
        
        print(f"✅ Total Dynamic QAT IDs Found: {len(extracted_qids)}")
        print(f"📌 Found QIDs List: {sorted(list(extracted_qids))}")
        print("--------------------------------------------------")
        
        # පේළියෙන් පේළිය Data මුද්‍රණය කිරීම
        for idx, row in enumerate(table_data):
            print(f"Row {idx+1}: {row}")
        print("==================================================\n")

        if not table_data:
            print("❌ No data rows captured from Dashboard!")
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
        print("🎉 SUCCESS: Entire Dashboard Data updated to Google Sheet 'QAT Raw Data'!")

if __name__ == "__main__":
    main()
