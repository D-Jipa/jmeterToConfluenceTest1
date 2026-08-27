import json
import re
import os
import sys
import datetime
import time
import requests
from bs4 import BeautifulSoup

# --- CONFIGURARE API ---
EMAIL = " "
API_TOKEN = " "
PAGE_ID = " "
DOMAIN = " "

LOCAL_HOST_URL = "http://localhost:8000"


def patch_jmeter_html_for_iframes(report_dir):
    pages_dir = os.path.join(report_dir, "content", "pages")
    if not os.path.exists(pages_dir):
        return

    for filename in os.listdir(pages_dir):
        if filename.endswith(".html"):
            filepath = os.path.join(pages_dir, filename)
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()

            content = re.sub(
                r'<link[^>]+href="[^"]*bootstrap\.min\.css"[^>]*>',
                '<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/twitter-bootstrap/3.3.7/css/bootstrap.min.css">',
                content,
                flags=re.IGNORECASE
            )
            content = re.sub(r'<!-- INJECTAT DE SCRIPTUL PYTHON.*?</body>', '</body>', content, flags=re.DOTALL)
            
            with open(filepath, "w", encoding="utf-8") as f:
                f.write(content)

def confluence_h1(text):
    return f'<table class="confluenceTable" style="width: 100%;"><tbody><tr><th class="confluenceTh"><h1 style="margin: 0px;">{text}</h1></th></tr></tbody></table>'

def html_vertical_table(rows):
    html = '<table class="confluenceTable"><tbody>'
    for row in rows:
        html += '<tr>'
        html += f'<th class="confluenceTh">{row[0]}</th>'
        html += f'<td class="confluenceTd">{row[1]}</td>'
        html += '</tr>'
    html += '</tbody></table>'
    return html

def html_horizontal_table(headers, rows):
    html = '<table class="confluenceTable"><tbody>'
    html += '<tr>' + ''.join(f'<th class="confluenceTh">{h}</th>' for h in headers) + '</tr>'
    for row in rows:
        html += '<tr>' + ''.join(f'<td class="confluenceTd">{c}</td>' for c in row) + '</tr>'
    html += '</tbody></table>'
    return html

def create_iframe_macro(url, height="480"):
    return f'<ac:structured-macro ac:name="iframe" ac:schema-version="1" data-layout="default"><ac:parameter ac:name="scrolling">no</ac:parameter><ac:parameter ac:name="src"><ri:url ri:value="{url}" /></ac:parameter><ac:parameter ac:name="width">100%</ac:parameter><ac:parameter ac:name="frameborder">hide</ac:parameter><ac:parameter ac:name="height">{height}</ac:parameter></ac:structured-macro><br/><br/>'

def parse_menu_dfs(ul_element, base_dir, current_category=None):
    items = []
    for li in ul_element.find_all('li', recursive=False):
        a_tag = li.find('a', recursive=False)
        if not a_tag:
            continue
        
        title = a_tag.get_text(strip=True)
        href = a_tag.get('href', '').strip()
        sub_ul = li.find('ul', recursive=False)
        
        if sub_ul:
            items.extend(parse_menu_dfs(sub_ul, base_dir, title))
        elif href and href.endswith('.html') and 'index.html' not in href:
            filepath = os.path.join(base_dir, href)
            items.append({
                "category": current_category or "Diverse",
                "page_title": title,
                "href": href,
                "filepath": filepath
            })
    return items

def extract_graphs_from_page(filepath):
    if not os.path.exists(filepath):
        return []
        
    with open(filepath, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
        
    graphs = []
    for portlet in soup.find_all("div", class_="portlet"):
        elem_id = portlet.get("id")
        if not elem_id: 
            continue
            
        title_tag = portlet.find(class_="span-title")
        title = title_tag.get_text(strip=True) if title_tag else f"Graph_{elem_id}"
        graphs.append({"id": elem_id, "title": title})
        
    return graphs

def generate_dynamic_iframes_dfs(report_dir, base_url):
    index_file = os.path.join(report_dir, "index.html")
    if not os.path.exists(index_file):
        return "<p><i>Eroare: Nu s-a gasit index.html pentru parsare.</i></p>"
        
    with open(index_file, "r", encoding="utf-8") as f:
        soup = BeautifulSoup(f, "lxml")
        
    side_menu = soup.find("ul", id="side-menu")
    if not side_menu:
        return "<p><i>Eroare: Structura JMeter nu contine id='side-menu'.</i></p>"
        
    pages = parse_menu_dfs(side_menu, report_dir)
    html_output = ""
    current_category = None
    ts = int(time.time()) 
    
    for page in pages:
        graphs = extract_graphs_from_page(page['filepath'])
        if not graphs: 
            continue 
            
        if page['category'] != current_category:
            html_output += f"<h3>{page['category']}</h3>"
            current_category = page['category']
            
        if page['page_title'] != page['category']:
            html_output += f"<h4>{page['page_title']}</h4>"
            
        for g in graphs:
            full_url = f"{base_url}/{page['href']}?v={ts}#{g['id']}"
            html_output += f"<h5>{g['title']}</h5>"
            html_output += create_iframe_macro(full_url, height="480")
            
    return html_output

def generate_full_html_report(report_dir):
    stat_file = os.path.join(report_dir, "statistics.json")
    folder_name = os.path.basename(os.path.abspath(report_dir))
    
    v_match = re.search(r'_V(\d+)_', folder_name)
    version = f"V{v_match.group(1)}" if v_match else "-"
    
    u_match = re.search(r'_(\d+)vuser', folder_name)
    users = f"{u_match.group(1)}" if u_match else "-"
    
    d_match = re.search(r'_(\d+min)_', folder_name)
    duration = d_match.group(1) if d_match else "-"

    total_samples = 0; total_errors = 0
    stats_rows = []; errors_rows = []
    
    # Lista de TPS (cat. 4)
    findings_tps_html = ""
    
    if os.path.exists(stat_file):
        with open(stat_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
            total_stats = stats.get("Total", {})
            total_samples = total_stats.get("sampleCount", 0)
            total_errors = total_stats.get("errorCount", 0)
            
            for key, val in stats.items():
                err_count = val.get('errorCount', 0)
                label = val.get("transaction", key)
                
                if key != "Total":
                    tps = val.get('throughput', 0)
                    findings_tps_html += f"<li>{label} - {tps:.2f} TPS</li>"
                    
                    if err_count > 0:
                        pct = (err_count / total_samples) * 100 if total_samples > 0 else 0
                        errors_rows.append([label, str(err_count), f"{pct:.2f}%"])
                
                stats_rows.append([
                    label, str(val.get("sampleCount", 0)),
                    str(err_count), f"{val.get('errorPct', 0):.2f}%",
                    f"{val.get('meanResTime', 0):.2f}", str(val.get("minResTime", 0)),
                    str(val.get("maxResTime", 0)), f"{val.get('throughput', 0):.2f}",
                    f"{val.get('receivedKBytesPerSec', 0):.2f}"
                ])

    error_text = "No errors occurred during the run." if total_errors == 0 else f"{total_errors} errors recorded during the run."

    # --- Cuprinsul (TOC) ---
    html = '<p><ac:structured-macro ac:name="toc" ac:schema-version="1"><ac:parameter ac:name="maxLevel">2</ac:parameter><ac:parameter ac:name="outline">false</ac:parameter></ac:structured-macro></p>'

    # --- 1. Execution summary ---
    html += confluence_h1("1. Execution summary")
    html += html_vertical_table([
        ["Component", "-"], 
        ["Version", version], 
        ["Resource group", "-"],
        ["Env. Infrastructure", "-"],
        ["Scenario details", "-"],
        ["Execution date", "-"], 
        ["Load generator", "-"], 
        ["Test type", "Load test"]
    ])
    
    # --- 2. Runtime configuration ---
    html += confluence_h1("2. Runtime configuration")
    html += html_vertical_table([
        ["Number of concurrent users", users], 
        ["Ramp up/Ramp down", "-"], 
        ["Pacing", "-"],
        ["Think time", "-"],
        ["Maximum load period duration", "-"],
        ["Total run period duration", duration]
    ])
    
    # --- 3. Specific configuration ---
    html += confluence_h1("3. Specific configuration")
    html += html_vertical_table([
        ["Test Data", "-"],
        ["jMeter script", "-"]
    ])
    
    # --- 4. Key findings ---
    html += confluence_h1("4. Key findings")
    html += html_vertical_table([
        ["Response times", "-"],
        ["Throughput", f"During the run the <b>transactions per second rate</b> was:<br/><ul>{findings_tps_html}</ul>"],
        ["Errors", error_text],
        ["Hardware", "-"]
    ])
    
    # --- 5. Performance Run Test results ---
    html += confluence_h1("5. Performance Run Test results")
    
    html += f"<h2>5.1. Response times - values (ms)</h2>"
    html += html_horizontal_table(["Label", "#Samples", "FAIL", "Error %", "Average", "Min", "Max", "Throughput", "KB/s"], stats_rows)
    
    html += f"<h2>5.2. Response times - comparison</h2><p></p>"
    
    html += f"<h2>5.3. Errors</h2>"
    if not errors_rows:
         html += html_horizontal_table(["Transaction name", "Error %"], [["No errors occurred during the run.", "0.00%"]])
    else:
         html += html_horizontal_table(["Transaction name", "#Errors", "% In all samples"], errors_rows)
         
    html += f"<h2>5.4. Analysis graphs</h2>"
    html += generate_dynamic_iframes_dfs(report_dir, LOCAL_HOST_URL)
    
    # --- 6. si 7. ---
    html += confluence_h1("6. Hardware resources consumption")
    html += f"<p></p>"
    
    html += confluence_h1("7. Query performance insight")
    html += f"<p></p>"
    
    # --- 8. Conclusions ---
    html += confluence_h1("8. Conclusions")
    html += html_vertical_table([
        ["Test status", "TEST PASSED" if total_errors == 0 else "TEST FAILED"],
        ["Conclusions", "-"]
    ])

    return html

def update_confluence_page(html_content):
    url = f"https://{DOMAIN}.atlassian.net/wiki/rest/api/content/{PAGE_ID}"
    auth = (EMAIL, API_TOKEN)
    headers = {"Accept": "application/json", "Content-Type": "application/json"}

    response = requests.get(url, headers=headers, auth=auth)
    if response.status_code != 200:
        print(f"[!] Eroare la citire: {response.text}")
        return
        
    page_data = response.json()
    
    payload = {
        "version": {"number": page_data['version']['number'] + 1},
        "title": page_data['title'],
        "type": "page",
        "body": {"storage": {"value": html_content, "representation": "storage"}}
    }

    put_response = requests.put(url, headers=headers, auth=auth, json=payload)
    if put_response.status_code == 200:
        print("[✓] SUCCES! Pagina a fost formatata perfect dupa designul Atlassian oficial.")
    else:
        print(f"[!] Eroare la update: {put_response.text}")

if __name__ == "__main__":
    folder = sys.argv[1] if len(sys.argv) > 1 else "."
    base_url = sys.argv[2] if len(sys.argv) > 2 else LOCAL_HOST_URL
    
    patch_jmeter_html_for_iframes(folder)
    
    final_html = generate_full_html_report(folder)
    update_confluence_page(final_html)