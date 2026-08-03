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
        
        # JS rendered elements සඳහා තත්පර 12ක් රැඳී සිටීම
        page.wait_for_timeout(12000)

        # පිටුවේ ඇති සියලුම Visible Tables සෙවීම
        tables = page.locator("table:visible").all()
        table_data = []
        best_table_rows = []

        if tables:
            # වඩාත්ම Rows ගණනක් ඇති Main Data Table එක පමණක් තෝරාගැනීම
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
                    table_data.append(row_vals)

        # Custom Data Grids (DIV based tables) සඳහා Fallback එකක්
        if not table_data:
            grid_rows = page.locator("div[role='row']:visible, .v-data-table tr:visible").all()
            for row in grid_rows:
                cells = row.locator("div[role='gridcell'], div[role='columnheader'], td, th").all()
                row_vals = [cell.inner_text().strip() for cell in cells]
                if any(row_vals):
                    table_data.append(row_vals)

        print(f"📊 Extracted {len(table_data)} rows of data.")

        if not table_data:
            print("❌ No main table data found on page!")
            return

        # Google Sheets Sync
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
