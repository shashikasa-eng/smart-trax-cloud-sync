import time
import json
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# Configuration from Environment Variables (for security in GitHub Actions)
SMART_URL = os.environ.get("SMART_URL", "https://smart.prod.trax.cloud.com/leader%20dashboard/dashboard")
USERNAME = os.environ.get("SMART_USERNAME", "YOUR_USERNAME")
PASSWORD = os.environ.get("SMART_PASSWORD", "YOUR_PASSWORD")
GOOGLE_CREDS_JSON = os.environ.get("GOOGLE_CREDS_JSON")  # JSON string of service account
SHEET_NAME = os.environ.get("SHEET_NAME", "SMART_Leader_Dashboard")

def main():
    print("🚀 Starting SMART Dashboard Automated Cloud Scraper...")
    
    # 1. Setup Google Sheets Client
    if GOOGLE_CREDS_JSON:
        creds_dict = json.loads(GOOGLE_CREDS_JSON)
        scope = ["https://spreadsheets.google.com/feeds", "https://www.googleapis.com/auth/drive"]
        creds = ServiceAccountCredentials.from_json_keyfile_dict(creds_dict, scope)
        client = gspread.authorize(creds)
        sheet = client.open(SHEET_NAME).worksheet("QAT Raw Data")
    else:
        print("⚠️ No Google Credentials JSON found in environment. Running in dry-run mode.")
        sheet = None

    # 2. Launch Headless Browser (Runs in Cloud)
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()

        print(f"🔑 Navigating to {SMART_URL}...")
        page.goto(SMART_URL, wait_until="networkidle")

        # Handle Login if redirected or login page is detected
        # Note: Adjust selectors according to SMART dashboard login form
        if "login" in page.url.lower() or page.query_selector("input[type='password']"):
            print("🔐 Logging into SMART Trax Cloud...")
            if page.query_selector("input[type='email']"):
                page.fill("input[type='email']", USERNAME)
            elif page.query_selector("input[type='text']"):
                page.fill("input[type='text']", USERNAME)
                
            page.fill("input[type='password']", PASSWORD)
            
            # Click Login / Submit button
            login_btn = page.query_selector("button[type='submit']") or page.query_selector("input[type='submit']") or page.query_selector(".login-btn")
            if login_btn:
                login_btn.click()
            else:
                page.keyboard.press("Enter")
                
            page.wait_for_timeout(7000) # Wait for dashboard table to load
            print("✅ Login completed.")

        # Ensure page content is fully loaded
        page.wait_for_selector("table", timeout=20000)
        time.sleep(3) # Wait for live AJAX data rendering

        # 3. Scrape Dashboard Data
        print("📊 Extracting table data...")
        table_rows = page.query_selector_all("table tbody tr")
        
        extracted_rows = []
        for row in table_rows:
            cols = row.query_selector_all("td")
            row_vals = [col.inner_text().strip() for col in cols]
            if any(row_vals): # Non-empty row
                extracted_rows.append(row_vals)

        print(f"✅ Extracted {len(extracted_rows)} records from dashboard.")

        # 4. Upload / Overwrite Data in Google Sheets
        if sheet and extracted_rows:
            print("☁️ Syncing data to Google Sheet...")
            headers = [
                "QAT ID", "QAT Name", "Project", "Trax Category Group", 
                "Trax Category Sub", "Task Type", "Task ID", "Task Duration", 
                "QAT Status", "Status Duration", "Last Login Time", "Start Shift Time"
            ]
            
            # Clear old rows and write fresh headers + scraped data
            sheet.clear()
            sheet.append_row(headers)
            sheet.append_rows(extracted_rows)
            
            print("🎉 Google Sheet updated successfully!")
        else:
            print("Result Data Preview:", extracted_rows[:3])

        browser.close()

if __name__ == "__main__":
    main()
