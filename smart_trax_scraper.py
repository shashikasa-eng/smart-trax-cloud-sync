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
        page.goto(url, wait_until="domcontentloaded", timeout=60000)

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
        
        # JS Render වීම සඳහා තත්පර 10ක් රඳවා ගැනීම
        page.wait_for_timeout(10000)

        # Table එක DOM එකට Attached වන තෙක් තත්පර 60ක් දක්වා රැඳී සිටීම
        try:
            page.wait_for_selector("table", state="attached", timeout=60000)
        except Exception as e:
            print("⚠️ Notice: Table state check timeout, proceeding to extract available content...")

        # Table එකේ Rows ලබා ගැනීම
        rows = page.locator("table tr").all()
        table_data = []

        for row in rows:
            cells = row.locator("th, td").all()
            row_vals = [cell.inner_text().strip() for cell in cells]
            if any(row_vals):
                table_data.append(row_vals)

        print(f"📊 Extracted {len(table_data)} rows of data.")

        if not table_data:
            print("❌ No table data found on page!")
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
