import os
import json
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from playwright.sync_api import sync_playwright

# 🎯 Targeted QIDs List (Total 35 QIDs)
TARGET_QIDS = [
    "K20748", "K20750", "K20752", "K20753", "K20754", "K20755", 
    "K20830", "K20831", "K20893", "K20818", "K16793", "K3777", 
    "K3129", "K4874", "K18603", "K18637", "K19747", "K19751", 
    "K19754", "K19757", "K20684", "K13227", "K21002", "K21004", 
    "K20232", "K20235", "K20242", "K20119", "K20120", "K20122", 
    "K16260", "K17205", "K20524", "K20896", "K18417"
]

def main():
    url = os.environ.get("SMART_URL")
    username = os.environ.get("SMART_USERNAME")
    password = os.environ.get("SMART_PASSWORD")
    sheet_name = os.environ.get("SHEET_NAME")
    creds_json = os.environ.get("GOOGLE_CREDS_JSON")

    if not all([url, username, password, sheet_name, creds_json]):
        raise Exception("Missing required environment variables in GitHub Secrets!")

    print(f"🚀 Starting Targeted QID Scraper for {len(TARGET_QIDS)} Users...")

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

        print("✅ Login completed. Waiting for Dashboard...")
        page.wait_for_timeout(10000)

        table_data = []
        found_qids = set()

        # ----------------------------------------------------------------------
        # 🔍 SEARCH / FILTER LOGIC PER QID
        # ----------------------------------------------------------------------
        search_box = page.locator("input[type='search'], input[placeholder*='Search'], input[aria-label*='Search']").first
        
        if search_box.is_visible():
            print("🎯 Search Box detected! Searching each QID directly...")
            for qid in TARGET_QIDS:
                try:
                    search_box.fill("")
                    search_box.fill(qid)
                    page.keyboard.press("Enter")
                    page.wait_for_timeout(2000)

                    rows = page.locator("table:visible tr, div[role='row']:visible").all()
                    for r in rows:
                        cells = r.locator("td, th, div[role='gridcell']").all()
                        row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]
                        if any(qid.lower() in v.lower() for v in row_vals):
                            if row_vals not in table_data:
                                table_data.append(row_vals)
                                found_qids.add(qid.upper())
                                print(f"✅ Found record for QID: {qid}")
                except Exception as ex:
                    print(f"⚠️ Search error for {qid}: {ex}")
        else:
            print("📜 Search box not found. Performing full pagination and QID matching...")
            
            # Smooth Scroll
            for _ in range(6):
                page.evaluate("window.scrollBy(0, 1000)")
                page.wait_for_timeout(1000)

            page_num = 1
            while True:
                rows = page.locator("table:visible tr, div[role='row']:visible").all()
                for r in rows:
                    cells = r.locator("td, th, div[role='gridcell']").all()
                    row_vals = [cell.inner_text().strip().replace('\n', ' ') for cell in cells]
                    if any(row_vals):
                        row_text = " ".join(row_vals).upper()
                        # Header row එකක් නම් ඇතුළත් කරගනී
                        if page_num == 1 and not table_data:
                            table_data.append(row_vals)
                        else:
                            # QID matching check
                            for qid in TARGET_QIDS:
                                if qid.upper() in row_text:
                                    found_qids.add(qid.upper())
                                    if row_vals not in table_data:
                                        table_data.append(row_vals)

                next_btn = page.locator("button[aria-label*='Next'], button:has-text('>'), .v-pagination__next button").first
                if next_btn.is_visible() and next_btn.is_enabled():
                    print(f"➡️ Moving to Page {page_num + 1}...")
                    next_btn.click()
                    page.wait_for_timeout(3000)
                    page_num += 1
                else:
                    break

        # ----------------------------------------------------------------------
        # 📋 DIAGNOSTIC PRINT LOG (GitHub Console එකේ බලාගැනීමට)
        # ----------------------------------------------------------------------
        print("\n==================================================")
        print("📊 --- SCRAPED SUMMARY & PREVIEW LOG ---")
        print("==================================================")
        print(f"🎯 Total Target QIDs Checked: {len(TARGET_QIDS)}")
        print(f"✅ Total Matched QIDs Found: {len(found_qids)}")
        print(f"📌 Found QIDs List: {sorted(list(found_qids))}")
        
        missing_qids = set(q.upper() for q in TARGET_QIDS) - found_qids
        if missing_qids:
            print(f"⚠️ Missing QIDs on Dashboard ({len(missing_qids)}): {sorted(list(missing_qids))}")
        
        print(f"\n📊 Total Extracted Rows (including header): {len(table_data)}")
        print("--------------------------------------------------")
        for idx, row in enumerate(table_data):
            print(f"Row {idx+1}: {row}")
        print("==================================================\n")

        if not table_data:
            print("❌ No matching QID rows found on Dashboard!")
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
        print("🎉 SUCCESS: Target QID Data updated to Google Sheet!")

if __name__ == "__main__":
    main()
