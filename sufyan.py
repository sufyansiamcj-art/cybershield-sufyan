from flask import Flask, render_template, request, send_file
import requests
import time
import sqlite3
from fpdf import FPDF
import os

app = Flask(__name__)

# --- 1. إعداد قاعدة البيانات ---
def init_db():
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute('''CREATE TABLE IF NOT EXISTS scans 
                 (id INTEGER PRIMARY KEY AUTOINCREMENT, url TEXT, result_summary TEXT, date TEXT)''')
    conn.commit()
    conn.close()


def scan_logic(target):
    if not target.startswith('http'): target = 'https://' + target
    raw_url = target.replace('https://', '').replace('http://', '').rstrip('/')
    results = []
    
    try:
        start_time = time.time()
        res_main = requests.get(target, timeout=5)
        latency = round((time.time() - start_time) * 1000, 2)
        
        results.append(f"Status: Online ({res_main.status_code})")
        results.append(f"Response Time: {latency} ms")
        
        
        check_files = {'.env': 'Environment File', 'admin/': 'Admin Panel', 'robots.txt': 'Robots File'}
        for f, desc in check_files.items():
            try:
                r = requests.get(f"https://{raw_url}/{f}", timeout=2, allow_redirects=False)
                status = "DANGER: Exposed" if r.status_code == 200 else "SAFE: Protected"
                results.append(f"Check {desc}: {status}")
            except:
                continue
        
        
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        summary = " | ".join(results)
        current_date = time.strftime("%Y-%m-%d %H:%M")
        c.execute("INSERT INTO scans (url, result_summary, date) VALUES (?, ?, ?)", (target, summary, current_date))
        conn.commit()
        conn.close()
    except:
        results.append("Error: Connection Failed")
    
    return results


@app.route('/', methods=['GET', 'POST'])
def index():
    results = None
    url = ""
    if request.method == 'POST':
        url = request.form.get('url')
        results = scan_logic(url)
    
    conn = sqlite3.connect('database.db')
    c = conn.cursor()
    c.execute("SELECT url, date, result_summary, id FROM scans ORDER BY id DESC LIMIT 5")
    history = c.fetchall()
    conn.close()
    
    return render_template('index.html', results=results, url=url, history=history)


@app.route('/download/<int:scan_id>')
def download_pdf(scan_id):
    try:
        conn = sqlite3.connect('database.db')
        c = conn.cursor()
        c.execute("SELECT url, result_summary, date FROM scans WHERE id=?", (scan_id,))
        row = c.fetchone()
        conn.close()

        if row:
            pdf = FPDF()
            pdf.add_page()
            pdf.set_font("Arial", 'B', 16)
            pdf.cell(200, 10, txt="CyberShield Security Report", ln=True, align='C')
            pdf.ln(10)
            
            pdf.set_font("Arial", size=12)
            pdf.cell(200, 10, txt=f"Website: {row[0]}", ln=True)
            pdf.cell(200, 10, txt=f"Date: {row[2]}", ln=True)
            pdf.ln(10)
            
            pdf.cell(200, 10, txt="Scan Findings:", ln=True)
            details = row[1].split(' | ')
            for line in details:
                
                clean_line = line.encode('latin-1', 'replace').decode('latin-1')
                pdf.cell(0, 10, txt=f"- {clean_line}", ln=True)
            
            report_path = f"report_{scan_id}.pdf"
            pdf.output(report_path)
            return send_file(report_path, as_attachment=True)
            
    except Exception as e:
        print(f"Error: {e}")
        return "Error generating PDF. Check Terminal."

    return "Not Found"

if __name__ == '__main__':
    init_db()
    app.run(debug=True)
    
if __name__ == '__main__':
    init_db()
    
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)