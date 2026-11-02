"""用真实浏览器截取六个运行记录页面，保存 PNG。"""
from pathlib import Path
import os
import subprocess

ROOT=Path(__file__).resolve().parents[1]
browser=Path(os.environ.get('HOMEWORK_BROWSER',r'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'))
if not browser.is_file(): raise SystemExit('Set HOMEWORK_BROWSER to a Chromium-based browser executable')
output=ROOT/'screenshots'; output.mkdir(exist_ok=True)
profile=ROOT.parent/'.screenshot-browser'
for page in sorted((ROOT/'evidence/pages').glob('Q*.html')):
    target=output/(page.stem+'.png')
    height={'Q1-1':1360,'Q1-2':1540,'Q1-3':1220,'Q2-1':1000,'Q2-2':1740,'Q2-3':1040}[page.stem]
    result=subprocess.run([str(browser),'--headless','--disable-gpu','--no-first-run','--no-default-browser-check',
        f'--user-data-dir={profile}','--hide-scrollbars',f'--window-size=1440,{height}',
        '--force-device-scale-factor=1',f'--screenshot={target}',page.as_uri()],
        stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=60,
        creationflags=subprocess.CREATE_NO_WINDOW if os.name=='nt' else 0)
    if result.returncode or not target.exists():
        raise RuntimeError(result.stderr.decode(errors='replace')[-2000:])
    print(target.name,target.stat().st_size)
