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
    logging.info("🚀 Starting Smart Grouped Dashboard Scraper...")

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
            # ⚡ FAST DOM EXTRACTION & INNER SCROLLING
            # ----------------------------------------------------------------------
            logging.info("⚡ Capturing all raw rows from Dashboard...")

            raw_rows_list = []

            for step in range(12):
                raw_extracted_rows = page.evaluate("""
                    () => {
                        const results = [];
                        const rowElements = document.querySelectorAll('tr, div[role="row"]');
                        
                        rowElements.forEach(row => {
                            const cells = row.querySelectorAll('td, th, div[role="gridcell"]');
                            const cellVals = Array.from(cells).map(c => c.innerText.trim().replace(/\\n/g, ' '));
                            if (cellVals.length > 1 && cellVals.some(v => v !== '')) {
                                results.push(cellVals);
                            }
                        });

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

                for row_vals in raw_extracted_rows:
                    if row_vals and len(row_vals) >= 2:
                        first_col = str(row_vals[0]).strip().upper()
                        if first_col.startswith("K"):
                            raw_rows_list.append(row_vals)

                page.wait_for_timeout(800)

            # ----------------------------------------------------------------------
            # 🧠 SMART GROUPING LOGIC (Group Multiple Tasks per QAT ID)
            # ----------------------------------------------------------------------
            logging.info("🧠 Processing Multi-Task Grouping per QAT ID...")

            grouped_qat_data = {}

            for r in raw_rows_list:
                qid = str(r[0]).strip().upper()
                name = r[1] if len(r) > 1 else ""
                project = r[2] if len(r) > 2 else ""
                cat1 = r[3] if len(r) > 3 else ""
                cat2 = r[4] if len(r) > 4 else ""
                task_type = r[5] if len(r) > 5 else ""
                task_id = r[6] if len(r) > 6 else ""
                task_dur = r[7] if len(r) > 7 else ""
                status = r[8] if len(r) > 8 else ""
                status_dur = r[9] if len(r) > 9 else ""
                last_login = r[10] if len(r) > 10 else ""
                start_shift = r[11] if len(r) > 11 else ""

                if qid not in grouped_qat_data:
                    grouped_qat_data[qid] = {
                        "QAT ID": qid,
                        "QAT Name": name,
                        "Project": set(),
                        "Trax Category Group Id": set(),
                        "Trax Category Group Name": set(),
                        "Task Type": set(),
                        "Task ID": set(),
                        "Task Duration": set(),
                        "QAT Status": status,
                        "Status Duration": status_dur,
                        "Last Login Time": last_login,
                        "Start Shift Time": start_shift
                    }

                # Set එකකට එකතු කරන්නේ Duplicates නැති කර තනි Record එකක් ලෙස සෑදීමටයි
                if project: grouped_qat_data[qid]["Project"].add(project)
                if cat1: grouped_qat_data[qid]["Trax Category Group Id"].add(cat1)
                if cat2: grouped_qat_data[qid]["Trax Category Group Name"].add(cat2)
                if task_type: grouped_qat_data[qid]["Task Type"].add(task_type)
                if task_id: grouped_qat_data[qid]["Task ID"].add(task_id)
                if task_dur: grouped_qat_data[qid]["Task Duration"].add(task_dur)
                
                # Active/Latest status එක update කිරීම
                if status: grouped_qat_data[qid]["QAT Status"] = status
                if status_dur: grouped_qat_data[qid]["Status Duration"] = status_dur

            # ----------------------------------------------------------------------
            # 📊 FORMULATE FINAL CLEAN TABLE DATA
            # ----------------------------------------------------------------------
            headers = ["QAT ID", "QAT Name", "Project", "Trax Category Group Id", "Trax Category Group Name", "Task Type", "Task ID", "Task Duration", "QAT Status", "Status Duration", "Last Login Time", "Start Shift Time"]
            final_table_data = [headers]

            for qid, data in grouped_qat_data.items():
                row = [
                    data["QAT ID"],
                    data["QAT Name"],
                    ", ".join(sorted(list(data["Project"]))),
                    ", ".join(sorted(list(data["Trax Category Group Id"]))),
                    ", ".join(sorted(list(data["Trax Category Group Name"]))),
                    ", ".join(sorted(list(data["Task Type"]))),
                    ", ".join(sorted(list(data["Task ID"]))),
                    ", ".join(sorted(list(data["Task Duration"]))),
                    data["QAT Status"],
                    data["Status Duration"],
                    data["Last Login Time"],
                    data["Start Shift Time"]
                ]
                final_table_data.append(row)

            # ----------------------------------------------------------------------
            # 📋 DIAGNOSTIC LOG ENGINE
            # ----------------------------------------------------------------------
            print("\n==================================================")
            print("📊 --- CLEAN GROUPED DASHBOARD SCRAPED LOG ---")
            print("==================================================")
            print(f"📊 Total Dynamic Unique QAT Profiles: {len(final_table_data) - 1}")
            print("--------------------------------------------------")

            for idx, row in enumerate(final_table_data):
                print(f"Row {idx+1}: {row}")
            print("==================================================\n")

            if len(final_table_data) <= 1:
                logging.error("❌ Extraction Failed: No data captured!")
                return

            # ----------------------------------------------------------------------
            # 🔄 GOOGLE SHEETS PIPELINE
            # ----------------------------------------------------------------------
            logging.info("🔄 Syncing Clean Grouped Data to Google Sheets...")
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
            worksheet.update('A1', final_table_data)
            logging.info("🎉 SUCCESS: Clean grouped dashboard updated to Google Sheet!")

        except Exception as ex:
            logging.error(f"❌ Error during execution: {ex}")
            raise ex
        finally:
            browser.close()

if __name__ == "__main__":
    main()
