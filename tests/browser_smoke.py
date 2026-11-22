"""Exercise real captured data at a Pages project subpath; screenshots are CI artifacts."""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil, tempfile, threading
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
class QuietHandler(SimpleHTTPRequestHandler):
 def log_message(self,*args):pass

def main():
 screenshots=ROOT/'browser-checks';screenshots.mkdir(exist_ok=True)
 with tempfile.TemporaryDirectory() as temporary:
  shutil.copytree(ROOT/'dist',Path(temporary)/'museumdrawer')
  server=ThreadingHTTPServer(('127.0.0.1',0),partial(QuietHandler,directory=temporary));threading.Thread(target=server.serve_forever,daemon=True).start()
  try:
   with sync_playwright() as p:
    browser=p.chromium.launch();page=browser.new_page(viewport={'width':1280,'height':1000});errors=[]
    page.on('pageerror',lambda error:errors.append(str(error)))
    page.goto(f'http://127.0.0.1:{server.server_port}/museumdrawer/');page.locator('#cards article').first.wait_for(timeout=60000)
    assert page.locator('#cards article').count()>0
    page.locator('#query').fill('zz_no_source_4982');assert page.locator('#empty').is_visible();assert page.locator('#stat-records').inner_text()=='0'
    page.locator('#query').fill('<img src=x onerror=alert(1)>');assert page.locator('#cards img').count()==0
    page.locator('#reset').click();page.locator('[data-region="halifax"]').click();assert 'Halifax' in page.locator('#coverage-details').inner_text()
    page.locator('#era').select_option('historic');assert page.locator('#stat-modern').inner_text()=='0'
    page.locator('#cards button').first.click();assert page.locator('#detail').is_visible();assert page.locator('#detail a').first.get_attribute('href').startswith('https://www.gbif.org/occurrence/')
    page.locator('#close-detail').click()
    with page.expect_download() as download:page.locator('#export').click()
    assert download.value.suggested_filename.startswith('museumdrawer-halifax-')
    page.locator('#reset').click();page.locator('#map .mapcell').first.click();assert page.locator('#clear-cell').is_visible();page.locator('#clear-cell').click()
    page.locator('#snapshot').select_option(index=2 if page.locator('#snapshot option').count()>2 else 1);page.locator('#load-status').wait_for(state='hidden',timeout=60000);assert page.locator('#cards article').count()>0
    page.locator('[data-region="langley"]').click();page.locator('#reset').click();page.evaluate('window.scrollTo(0,0)');page.screenshot(path=str(screenshots/'desktop.png'),full_page=True)
    page.set_viewport_size({'width':390,'height':844})
    page.screenshot(path=str(screenshots/'mobile.png'),full_page=True)
    geometry=page.evaluate("""() => ({viewport:innerWidth,document:document.documentElement.scrollWidth,
      wide:[...document.querySelectorAll('body *')].map(el=>({tag:el.tagName,id:el.id,
        className:typeof el.className==='string'?el.className:'',right:el.getBoundingClientRect().right}))
        .filter(el=>el.right>innerWidth+1).slice(0,20)})""")
    assert geometry['document']<=geometry['viewport']+1,geometry
    assert not errors,errors;browser.close()
  finally:server.shutdown()
 print('Browser checks passed: subpath, real data, filters, detail, CSV, map, history and mobile')
if __name__=='__main__':main()
