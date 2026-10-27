"""Bounded music dialogue and a dedicated, visible Brave music window."""
import os
import subprocess
import re
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from urllib.parse import urlencode


class YouTubePlayer:
    def __init__(self, profile=None, muted=False, headless=False):
        self._profile = profile or Path(__file__).resolve().parent.parent / 'data' / 'music-brave'
        self._muted = muted
        self._headless = headless
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix='ArtemisMusic')
        self._context = self._page = self._playwright = None
        self._browser = self._process = None

    def perform(self, action, query=''):
        # Every Playwright operation stays on its owning worker thread.
        return self._pool.submit(self._perform, action, query).result()

    def _ensure_page(self):
        if self._page is not None and not self._page.is_closed():
            return self._page
        if self._context is not None:
            try:self._context.close()
            except Exception:pass
        if self._playwright is None:
            from playwright.sync_api import sync_playwright
            self._playwright = sync_playwright().start()
        args=['--autoplay-policy=no-user-gesture-required']
        if self._muted:args.append('--mute-audio')
        candidates=[Path(os.environ.get('PROGRAMFILES',r'C:\Program Files'))/'BraveSoftware/Brave-Browser/Application/brave.exe',
                    Path(os.environ.get('PROGRAMFILES(X86)',r'C:\Program Files (x86)'))/'BraveSoftware/Brave-Browser/Application/brave.exe',
                    Path(os.environ.get('LOCALAPPDATA',''))/'BraveSoftware/Brave-Browser/Application/brave.exe']
        executable=next((str(path) for path in candidates if path.is_file()),None)
        if executable is None:raise RuntimeError('Brave browser is not installed.')
        # Start the installed browser normally and connect its local DevTools endpoint.
        # This profile is dedicated to Artemis and persists guest consent/session state.
        self._profile=Path(self._profile)
        self._profile.mkdir(parents=True,exist_ok=True)
        port_file=self._profile/'DevToolsActivePort'
        if port_file.exists():port_file.unlink()
        args += ['--user-data-dir='+str(self._profile),'--remote-debugging-port=0',
                 '--remote-debugging-address=127.0.0.1','--no-first-run',
                 '--no-default-browser-check','--new-window']
        if self._headless:args.append('--headless=new')
        self._process=subprocess.Popen([executable]+args+['about:blank'],
                                       stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
        for _ in range(60):
            if port_file.is_file():break
            if self._process.poll() is not None:raise RuntimeError('Brave music profile is already open or could not start.')
            time.sleep(0.2)
        port=int(port_file.read_text().splitlines()[0])
        if not 1<=port<=65535:raise RuntimeError('Invalid local browser endpoint.')
        self._browser=self._playwright.chromium.connect_over_cdp('http://127.0.0.1:'+str(port),timeout=12000)
        self._context=self._browser.contexts[0]
        self._page=self._context.pages[0] if self._context.pages else self._context.new_page()
        self._page.set_default_timeout(10000)
        return self._page

    def _perform(self, action, query):
        try:
            if action in ('pause','stop','resume'):
                if self._page is None or self._page.is_closed():
                    return {'ok':False,'reply':'There is no Artemis music session open. Ask me to play music first.'}
                page=self._page
                if action=='stop':
                    page.goto('about:blank',wait_until='domcontentloaded',timeout=15000)
                    return {'ok':True,'reply':'Stopped the music.'}
                state=page.evaluate('''async (action) => {
                    const v=document.querySelector('video');
                    if(!v)return false;
                    if(action==='pause')v.pause();else await v.play();
                    return action==='pause'?v.paused:!v.paused;
                }''',action)
                return {'ok':bool(state),'reply':('Paused the music.' if action=='pause' else 'Resumed the music.') if state else 'The YouTube player is not ready.'}
            page=self._ensure_page()
            page.goto('https://www.youtube.com/results?'+urlencode({'search_query':query}),
                      wait_until='domcontentloaded',timeout=25000)
            # Use the non-personalized option if YouTube presents a consent page.
            reject=page.get_by_role('button',name=re.compile(r'^(Reject all|Alle ablehnen)$',re.I))
            try:reject.first.click(timeout=2500)
            except Exception:pass
            if page.url.startswith('https://accounts.google.com/'):
                return {'ok':False,'reply':'YouTube is requiring account verification for this request. I cannot start this video as a guest. Try another song or use your regular Brave window.'}
            result=page.locator('ytd-video-renderer a#video-title').first
            result.wait_for(state='visible',timeout=15000)
            title=result.get_attribute('title') or result.inner_text()
            href=result.get_attribute('href') or ''
            video_id=re.search(r'(?:\?|&)v=([A-Za-z0-9_-]{11})(?:&|$)',href)
            if not href.startswith('/watch?') or not video_id:
                raise RuntimeError('No regular YouTube video result available.')
            page.goto('https://www.youtube.com/watch?v='+video_id.group(1),
                      wait_until='domcontentloaded',timeout=25000)
            if page.url.startswith('https://accounts.google.com/'):
                return {'ok':False,'reply':'YouTube requires verification for this video. I cannot start it as a guest. Try another song.'}
            page.locator('video').wait_for(state='attached',timeout=15000)
            page.evaluate('''async () => {
                const v=document.querySelector('video');
                v.muted=false; await v.play();
            }''')
            page.wait_for_function("() => {const v=document.querySelector('video');return v && !v.paused && v.readyState>=2}",timeout=15000)
            # Report transport playback, not a guarantee that the requested song has passed any ad.
            return {'ok':True,'reply':'Started YouTube playback for '+query+'. YouTube may play an ad first.',
                    'title':str(title)[:250]}
        except ImportError:
            return {'ok':False,'reply':'YouTube playback needs the Artemis browser-control component installed.'}
        except Exception as error:
            print('[Music playback]',type(error).__name__,str(error)[:600],flush=True)
            return {'ok':False,'reply':'I could not start YouTube playback. Check the Artemis music window for a connection, sign-in, or verification message, then try again.'}

    def close(self):
        def cleanup():
            try:
                if self._browser is not None:
                    # Closing a CDP connection alone can leave the owned browser running.
                    try:self._browser.new_browser_cdp_session().send('Browser.close')
                    except Exception:pass
                    self._browser.close()
            finally:
                if self._process is not None and self._process.poll() is None:
                    try:self._process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        self._process.terminate()
                        self._process.wait(timeout=3)
                if self._playwright is not None:self._playwright.stop()
            self._context=self._page=self._playwright=None
        try:self._pool.submit(cleanup).result(timeout=10)
        finally:self._pool.shutdown(wait=False,cancel_futures=True)


class MusicService:
    def __init__(self, player=None):
        self._player=player or YouTubePlayer()
        self._pending_until=0
        self._lock=threading.Lock()

    def execute(self, text):
        if not isinstance(text,str) or len(text)>3000:return {'handled':False}
        command=re.sub(r'\s+',' ',text).strip(' .!?')
        command=re.sub(r'^(?:hey\s+)?artemis[,!:. ]+','',command,flags=re.I)
        command=re.sub(r'^(?:(?:can|could|would) you (?:please )?|please )','',command,flags=re.I)
        low=command.casefold()
        with self._lock:
            pending=time.monotonic()<self._pending_until
            self._pending_until=0
            if pending and low in ('cancel','never mind','nevermind','forget it','no thanks'):
                return {'handled':True,'reply':'Okay, cancelled the music request.'}
            controls={'pause music':'pause','pause the music':'pause','pause youtube':'pause',
                      'stop music':'stop','stop the music':'stop','stop youtube':'stop',
                      'resume music':'resume','resume the music':'resume','resume youtube':'resume'}
            if low in controls:
                return {'handled':True,**self._player.perform(controls[low])}
            request=re.fullmatch(r'play\s+(.+?)(?:\s+on\s+you\s*tube)?',command,re.I)
            query=request.group(1).strip() if request else None
            if request and query.casefold() in ('music','some music','a song','songs','something','some songs'):
                self._pending_until=time.monotonic()+120
                return {'handled':True,'reply':'What kind of music would you like? You can say a genre, artist, or song name.', 'awaiting_music':True}
            if query is None and pending:
                # A new request must not be swallowed as a music answer.
                if re.match(r'^(?:open|launch|start|what|when|where|how|why|tell|calculate|weather|forecast|explain|stop|pause)\b',low):
                    return {'handled':False}
                if len(command.split())>20:return {'handled':False}
                query=re.sub(r'^(?:i (?:want|would like)(?: to (?:hear|listen to))?|i\x27d like|some)\s+','',command,flags=re.I)
            if query is None:return {'handled':False}
            query=re.sub(r'\s+please$','',query,flags=re.I).strip()
            if not query or len(query)>200:
                return {'handled':True,'reply':'Please give me a shorter genre, artist, or song name.'}
            return {'handled':True,**self._player.perform('play',query)}

    def close(self):self._player.close()
