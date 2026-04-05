#!/usr/bin/env python3
"""
Convert the latest CIVITAE stress test .txt report to a styled HTML file.
Usage: python3 make_report.py [optional/path/to/report.txt]
"""

import sys, os, re, glob
from datetime import datetime

REPORT_DIR = os.path.join(os.path.dirname(__file__), "reports")

# Find latest report
if len(sys.argv) > 1:
    txt_path = sys.argv[1]
else:
    files = sorted(glob.glob(os.path.join(REPORT_DIR, "stress-*.txt")))
    if not files:
        print("No reports found in reports/"); sys.exit(1)
    txt_path = files[-1]

with open(txt_path) as f:
    raw = f.read()

lines = raw.splitlines()

# ── Parse sections ─────────────────────────────────────────────────────────────
def extract(pattern, default="—"):
    m = re.search(pattern, raw)
    return m.group(1).strip() if m else default

score_pct   = extract(r"Score\s*:\s*([\d.]+%)")
passed      = extract(r"Passed\s*:\s*(\d+)")
failed      = extract(r"Failed\s*:\s*(\d+)")
agents_n    = extract(r"Agents provisioned\s*:\s*(\d+)")
missions_n  = extract(r"Missions posted\s*:\s*(\d+)")
meeting_id  = extract(r"Meeting conducted\s*:\s*(YES[^\n]+|NO)")
target      = extract(r"Target:\s*(https?://[^\s]+)")
report_date = extract(r"CIVITAE STRESS TEST REPORT\s+(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})")

# Parse phases from the log section
phase_blocks = []
current_phase = None
current_items = []
in_log = False

for line in lines:
    if "── FULL TEST LOG" in line:
        in_log = True; continue
    if not in_log:
        continue
    if line.startswith("  PHASE") and "═" not in line:
        if current_phase:
            phase_blocks.append((current_phase, current_items))
        current_phase = line.strip()
        current_items = []
    elif line.strip().startswith(("✅","❌","⚠️","📊","⏱")):
        current_items.append(line.strip())

if current_phase:
    phase_blocks.append((current_phase, current_items))

# Parse timings
timings = []
in_timings = False
for line in lines:
    if "── ENDPOINT TIMINGS" in line:
        in_timings = True; continue
    if in_timings and line.strip().startswith("──"):
        in_timings = False
    if in_timings and line.strip():
        # e.g.  "adjourn-meeting                        0.358s  (n=1)"
        m = re.match(r"\s+([\w/:\-]+)\s+([\d.]+)s\s+\(n=(\d+)\)", line)
        if m:
            timings.append((m.group(1), float(m.group(2)), int(m.group(3))))

# Parse errors
errors = []
in_errors = False
for line in lines:
    if "── ERRORS" in line:
        in_errors = True; continue
    if in_errors and line.strip().startswith("──"):
        in_errors = False
    if in_errors and "⚠️" in line:
        errors.append(re.sub(r"⚠️\s*", "", line).strip())

# ── HTML ───────────────────────────────────────────────────────────────────────
score_num = float(score_pct.replace("%","")) if score_pct != "—" else 0
score_color = "#4CAF50" if score_num >= 95 else "#FF9800" if score_num >= 80 else "#F44336"

def phase_html(name, items):
    rows = ""
    for item in items:
        if item.startswith("✅"):
            cls, sym = "pass", "✅"
        elif item.startswith("❌"):
            cls, sym = "fail", "❌"
        elif item.startswith("⚠️"):
            cls, sym = "warn", "⚠️"
        else:
            cls, sym = "info", item[0]
        text = re.sub(r"^[✅❌⚠️📊⏱ ]+", "", item)
        rows += f'<tr class="{cls}"><td class="sym">{sym}</td><td>{text}</td></tr>\n'
    return f"""
<div class="phase">
  <h3>{name}</h3>
  <table><tbody>{rows}</tbody></table>
</div>"""

phases_html = "\n".join(phase_html(n, i) for n, i in phase_blocks)

timing_rows = ""
for ep, avg, n in sorted(timings, key=lambda x: -x[1]):
    bar_w = min(int(avg / 1.5 * 100), 100)
    clr = "#4CAF50" if avg < 0.5 else "#FF9800" if avg < 1.0 else "#F44336"
    timing_rows += f"""
<tr>
  <td class="ep-name">{ep}</td>
  <td><div class="bar-wrap"><div class="bar" style="width:{bar_w}%;background:{clr}"></div></div></td>
  <td class="ep-time">{avg:.3f}s</td>
  <td class="ep-n">n={n}</td>
</tr>"""

error_rows = ""
for e in errors:
    error_rows += f'<tr><td>⚠️</td><td>{e}</td></tr>'

error_section = f"""
<div class="section">
  <h2>Errors</h2>
  <table class="error-table"><tbody>{error_rows}</tbody></table>
</div>""" if errors else ""

html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>CIVITAE Stress Test Report — {report_date}</title>
<style>
  @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:wght@700&family=DM+Sans:wght@400;500;600&family=DM+Mono&display=swap');

  :root {{
    --bg:     #0B0D10;
    --panel:  #12151A;
    --border: #1E2228;
    --gold:   #C4923A;
    --text:   #E8EAF0;
    --muted:  #7A8090;
    --pass:   #3DAA6A;
    --fail:   #D84040;
    --warn:   #D48C2E;
  }}

  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ background: var(--bg); color: var(--text); font-family: 'DM Sans', sans-serif; padding: 40px 24px; min-height: 100vh; }}

  header {{ max-width: 960px; margin: 0 auto 40px; border-bottom: 1px solid var(--border); padding-bottom: 24px; }}
  header h1 {{ font-family: 'Playfair Display', serif; color: var(--gold); font-size: 2rem; letter-spacing: 0.04em; }}
  header p {{ color: var(--muted); font-size: 0.85rem; margin-top: 6px; font-family: 'DM Mono', monospace; }}

  .scorecard {{ display: flex; gap: 16px; flex-wrap: wrap; max-width: 960px; margin: 0 auto 36px; }}
  .card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: 20px 24px; flex: 1; min-width: 140px; }}
  .card .label {{ font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: var(--muted); margin-bottom: 8px; }}
  .card .value {{ font-family: 'DM Mono', monospace; font-size: 1.8rem; font-weight: 700; }}
  .card.score .value {{ color: {score_color}; }}
  .card.pass  .value {{ color: var(--pass); }}
  .card.fail  .value {{ color: var(--fail); }}
  .card.meta  .value {{ font-size: 1.1rem; color: var(--text); }}

  .content {{ max-width: 960px; margin: 0 auto; display: grid; gap: 24px; }}
  .section {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  .section h2 {{ font-family: 'Playfair Display', serif; color: var(--gold); padding: 16px 20px; font-size: 1rem; letter-spacing: 0.05em; border-bottom: 1px solid var(--border); }}

  .phase {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
  .phase h3 {{ font-size: 0.78rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--muted); padding: 12px 16px; border-bottom: 1px solid var(--border); }}
  .phase table {{ width: 100%; border-collapse: collapse; }}
  .phase td {{ padding: 8px 16px; font-size: 0.875rem; vertical-align: top; }}
  .phase .sym {{ width: 28px; font-size: 1rem; }}
  .phase tr.pass {{ background: rgba(61,170,106,0.06); }}
  .phase tr.fail {{ background: rgba(216,64,64,0.07); }}
  .phase tr.warn {{ background: rgba(212,140,46,0.06); }}
  .phase tr.info {{ color: var(--muted); font-size: 0.82rem; }}
  .phase tr + tr {{ border-top: 1px solid rgba(255,255,255,0.03); }}

  .timing-table {{ width: 100%; border-collapse: collapse; }}
  .timing-table td {{ padding: 9px 20px; font-size: 0.82rem; vertical-align: middle; border-top: 1px solid var(--border); }}
  .ep-name {{ font-family: 'DM Mono', monospace; color: var(--text); width: 240px; }}
  .ep-time {{ font-family: 'DM Mono', monospace; color: var(--gold); text-align: right; white-space: nowrap; }}
  .ep-n    {{ color: var(--muted); text-align: right; width: 60px; }}
  .bar-wrap {{ background: rgba(255,255,255,0.06); border-radius: 4px; height: 8px; width: 100%; }}
  .bar {{ height: 8px; border-radius: 4px; }}

  .error-table {{ width: 100%; border-collapse: collapse; }}
  .error-table td {{ padding: 9px 20px; font-size: 0.82rem; border-top: 1px solid var(--border); font-family: 'DM Mono', monospace; color: var(--warn); }}

  footer {{ max-width: 960px; margin: 40px auto 0; color: var(--muted); font-size: 0.75rem; font-family: 'DM Mono', monospace; text-align: center; border-top: 1px solid var(--border); padding-top: 16px; }}
</style>
</head>
<body>

<header>
  <h1>CIVITAE — Stress Test Report</h1>
  <p>{report_date} &nbsp;·&nbsp; {target}</p>
</header>

<div class="scorecard">
  <div class="card score">
    <div class="label">Score</div>
    <div class="value">{score_pct}</div>
  </div>
  <div class="card pass">
    <div class="label">Passed</div>
    <div class="value">{passed}</div>
  </div>
  <div class="card fail">
    <div class="label">Failed</div>
    <div class="value">{failed}</div>
  </div>
  <div class="card meta">
    <div class="label">Agents Provisioned</div>
    <div class="value">{agents_n}</div>
  </div>
  <div class="card meta">
    <div class="label">Missions Posted</div>
    <div class="value">{missions_n}</div>
  </div>
  <div class="card meta">
    <div class="label">Meeting</div>
    <div class="value" style="font-size:0.85rem">{meeting_id}</div>
  </div>
</div>

<div class="content">

  {error_section}

  {phases_html}

  <div class="section">
    <h2>Endpoint Timings</h2>
    <table class="timing-table">
      <tbody>{timing_rows}</tbody>
    </table>
  </div>

</div>

<footer>CIVITAE™ Stress Test Suite &nbsp;·&nbsp; Report generated {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</footer>
</body>
</html>"""

html_path = txt_path.replace(".txt", ".html")
with open(html_path, "w") as f:
    f.write(html)

print(f"✅  HTML report → {html_path}")
