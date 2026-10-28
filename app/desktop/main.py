"""ARTEMIS Desktop V2: WebView2 interface with 50/50 crystal/water GPU material.
Standalone replacement for desktop/ only. Does not modify artemis/ or Stage 7.5.
"""
import argparse
import os
import sys
import threading
import webbrowser
import json
from pathlib import Path
from server import make_server
from whisper_input import WhisperInput
from speech_output import SpeechOutput
from desktop_state import DesktopState
from app_launcher import AppLauncher
from everyday import Everyday
from tool_router import Tool, ToolRouter
from personal_memory import PersonalMemory
from document_search import DocumentSearch
from reminders import Reminders
from daily_briefing import DailyBriefing
from model_settings import ModelSettings
from performance_log import PERFORMANCE
from briefing_schedule import BriefingSchedule

class WindowBridge:
    """Windows control + local push-to-talk only. No application execution exposed."""
    def __init__(self):
        self._window = None
        self._apps = AppLauncher()
        self._everyday = Everyday()
        self._memory = PersonalMemory()
        self._documents = DocumentSearch()
        self._reminders = Reminders()
        self._models = ModelSettings()
        self._briefing = DailyBriefing(self._everyday,self._reminders)
        self._briefing_schedule = BriefingSchedule(self._briefing)
        self._tools = ToolRouter([
            Tool('briefing', 'On-demand weather and reminder summary for today', self._briefing.execute),
            Tool('reminders', 'Create, list and cancel persistent one-shot reminders', self._reminders.execute),
            Tool('documents', 'Search, list and remove explicitly indexed documents', self._documents.execute),
            Tool('memory', 'Explicitly save, list, search, edit and forget personal facts', self._memory.execute),
            Tool('everyday', 'Weather, local date/time, basic arithmetic and help', self._everyday.execute),
            Tool('apps', 'Explicit installed-app launch requests', self._apps.execute),
        ])
        self._voice = WhisperInput()
        self._speech = SpeechOutput()
        self._saved = DesktopState()
        self._quiet_mode = self._saved.load()['preferences']['quiet']
        self._handsfree_enabled = False
        self._interaction_lock = threading.RLock()
        self._speech.set_enabled(not self._quiet_mode and self._saved.load()['preferences']['speechEnabled'])
        self._is_fullscreen = False
        self._maximized = False
        self._window_lock = threading.Lock()
        self._mini_mode = 'full'
        self._full_bounds = None
        self._mini_file = Path(__file__).resolve().parent.parent / 'data' / 'mini-window.json'
        self._mini_position = None
        self._mini_top = False
        self._position_timer = None
        self._mini_save_lock = threading.Lock()
        try:
            data = json.loads(self._mini_file.read_text(encoding='utf-8'))
            if type(data.get('x')) is int and type(data.get('y')) is int:
                self._mini_position = (data['x'], data['y'])
            self._mini_top = data.get('onTop') is True
        except (OSError, ValueError, TypeError):
            pass

    def _save_mini(self):
        with self._mini_save_lock:
            self._write_mini()

    def _write_mini(self):
        try:
            self._mini_file.parent.mkdir(parents=True, exist_ok=True)
            x, y = self._mini_position or (80, 80)
            tmp = self._mini_file.with_suffix('.tmp')
            tmp.write_text(json.dumps(dict(x=x, y=y, onTop=self._mini_top)), encoding='utf-8')
            os.replace(tmp, self._mini_file)
        except OSError as exc:
            print('Mini position save failed:', exc, flush=True)

    def _remember_position(self, x, y):
        if self._mini_mode == 'full':
            return
        self._mini_position = (int(x), int(y))
        if self._position_timer:
            self._position_timer.cancel()
        self._position_timer = threading.Timer(.5, self._save_mini)
        self._position_timer.daemon = True
        self._position_timer.start()

    def get_mini_state(self):
        return {'ok': True, 'mode': self._mini_mode, 'onTop': self._mini_top}

    def window_action(self, action):
        if action not in ('minimize', 'maximize', 'close') or self._window is None:
            return {'ok': False, 'error': 'Invalid window action'}
        try:
            def apply():
                if action == 'minimize':
                    self._window.minimize()
                elif action == 'maximize':
                    if self._mini_mode != 'full':
                        return {'ok': False, 'error': 'Choose Full before maximizing.'}
                    if self._maximized:
                        self._window.restore()
                    else:
                        self._window.maximize()
                    self._maximized = not self._maximized
                else:
                    if self._position_timer:
                        self._position_timer.cancel()
                    if self._mini_mode != 'full':
                        self._save_mini()
                    self._window.destroy()
                return {'ok': True, 'maximized': self._maximized}
            return self._on_ui_thread(apply)
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def _on_ui_thread(self, action):
        """Marshal native layout work; never set WinForms properties on bridge threads."""
        native = getattr(self._window, 'native', None)
        if native is None:
            # Test doubles must explicitly implement their own thread contract.
            if hasattr(self._window, '_test_dispatch'):
                return self._window._test_dispatch(action)
            raise RuntimeError('Native window is not ready')
        if not native.InvokeRequired:
            return action()
        from System import Action
        done = threading.Event()
        result = {}
        def execute():
            # A queued request must not resize later after its caller timed out.
            if done.is_set():
                return
            try:
                result['value'] = action()
            except Exception as exc:
                result['error'] = exc
            finally:
                done.set()
        native.BeginInvoke(Action(execute))
        if not done.wait(5):
            done.set()
            raise RuntimeError('Window did not respond within 5 seconds')
        if 'error' in result:
            raise result['error']
        return result.get('value')

    def set_mini_top(self, enabled):
        if self._window is None:
            return {'ok': False, 'error': 'Window not ready'}
        try:
            self._on_ui_thread(lambda: setattr(self._window, 'on_top', bool(enabled) if self._mini_mode != 'full' else False))
            self._mini_top = bool(enabled)
            self._save_mini()
            return self.get_mini_state()
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def set_mini_mode(self, mode):
        if mode not in ('full', 'mini', 'chat') or self._window is None:
            return {'ok': False, 'error': 'Invalid layout or window not ready'}
        try:
            def apply():
                if mode == self._mini_mode:
                    return self.get_mini_state()
                if self._is_fullscreen:
                    self._window.toggle_fullscreen()
                    self._is_fullscreen = False
                if self._mini_mode == 'full':
                    self._full_bounds = (self._window.x, self._window.y, self._window.width, self._window.height)
                    self._window.restore()
                    self._maximized = False
                self._mini_mode = mode
                self._window.on_top = self._mini_top if mode != 'full' else False
                if mode == 'full':
                    x,y,w,h = self._full_bounds or (80,80,1440,880)
                else:
                    w,h = (280,300) if mode == 'mini' else (420,620)
                    x,y = self._mini_position or (80,80)
                    # Recover positions when a monitor has been disconnected.
                    import webview
                    screens = webview.screens
                    valid = [s for s in screens if s.x <= x < s.x+s.width-80 and s.y <= y < s.y+s.height-60]
                    s = (valid or screens)[0] if screens else None
                    if s:
                        x = max(s.x, min(x, s.x+s.width-w))
                        y = max(s.y, min(y, s.y+s.height-h))
                self._window.resize(w,h)
                self._window.move(x,y)
                return self.get_mini_state()
            return self._on_ui_thread(apply)
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def set_fullscreen(self, enabled):
        if enabled and self._mini_mode != 'full':
            return {'ok': False, 'error': 'Choose Full before entering fullscreen.'}
        if self._window is None:
            return {'ok': False, 'error': 'The native window is not ready'}
        try:
            with self._window_lock:
                enabled = bool(enabled)
                if enabled != self._is_fullscreen:
                    self._window.toggle_fullscreen()
                    self._is_fullscreen = enabled
                return {'ok': True, 'fullscreen': self._is_fullscreen}
        except Exception as exc:
            return {'ok': False, 'error': str(exc)}

    def toggle_fullscreen(self):
        return self.set_fullscreen(not self._is_fullscreen)

    def get_fullscreen(self):
        return {'ok': True, 'fullscreen': self._is_fullscreen}

    def start_listening(self):
        if self._quiet_mode:
            return {'ok': False, 'error': 'Quiet mode is on. Use text chat.'}
        return self._voice.start()

    def set_handsfree(self, enabled):
        with self._interaction_lock:
            if enabled and self._quiet_mode:
                return {'ok': False, 'error': 'Turn off Quiet mode before enabling hands-free.'}
            if enabled:
                if self._voice.status().get('state') in ('listening', 'transcribing'):
                    return {'ok': False, 'error': 'Finish the current recording first.'}
                self._voice.cancel()
                self._speech.clear_error()
            self._handsfree_enabled = bool(enabled)
            print('[Hands-free]', 'enabled' if enabled else 'disabled',flush=True)
            if not enabled:
                self._voice.cancel()
            return {'ok': True, 'enabled': self._handsfree_enabled}

    def start_handsfree_turn(self):
        with self._interaction_lock:
            if self._quiet_mode or not self._handsfree_enabled:
                return {'ok': False, 'error': 'Hands-free is off.'}
            if self._speech.status()['playing']:
                return {'ok': False, 'error': 'Wait for Isabella to finish.'}
            result=self._voice.start(auto_stop=True)
            print('[Hands-free] recording start',result,flush=True)
            return result

    def stop_listening(self):
        return self._voice.stop()

    def voice_status(self):
        return self._voice.status()

    def speech_status(self):
        return self._speech.status()

    def set_speech_enabled(self, enabled):
        if self._quiet_mode and enabled:
            return {'ok': False, 'error': 'Quiet mode keeps Isabella muted.'}
        return self._speech.set_enabled(enabled)

    def speak_reply(self, text):
        if self._quiet_mode:
            return {'ok': False, 'error': 'Speech output is muted'}
        return self._speech.speak(text)

    def stop_speaking(self):
        self.set_handsfree(False)
        return self._speech.stop()

    def load_desktop_state(self):
        return {'ok': True, **self._saved.load()}

    def handle_app_command(self, text):
        # Compatibility for older desktop clients.
        return self.handle_command(text)

    def handle_command(self, text):
        return self._tools.execute(text)

    def list_tools(self):
        return self._tools.catalog()

    def get_briefing_schedule(self):
        try:return {'ok':True,**self._briefing_schedule.get()}
        except Exception:return {'ok':False,'error':'Could not read the briefing schedule.'}

    def set_briefing_schedule(self,enabled,at):
        try:return {'ok':True,**self._briefing_schedule.configure(enabled,at)}
        except ValueError as exc:return {'ok':False,'error':str(exc)}
        except Exception:return {'ok':False,'error':'Could not save the briefing schedule.'}

    def check_scheduled_briefing(self):
        try:return {'ok':True,**self._briefing_schedule.check()}
        except Exception:return {'ok':False,'error':'Could not prepare the scheduled briefing. The next check will retry.'}

    def dismiss_scheduled_briefing(self,date):
        try:return {'ok':self._briefing_schedule.dismiss(date)}
        except Exception:return {'ok':False,'error':'Could not dismiss this briefing.'}

    def get_performance(self):
        return {'ok':True,**PERFORMANCE.snapshot()}

    def clear_performance(self):
        PERFORMANCE.clear()
        return {'ok':True}

    def get_ollama_models(self):
        try:
            selected=self._models.get()
            return {'ok':True,'selected':selected,'models':self._models.available()}
        except Exception:return {'ok':False,'error':'Could not load model settings or reach Ollama. Check services and try again.'}

    def select_ollama_model(self,name):
        try:return {'ok':True,'selected':self._models.select(name)}
        except ValueError as exc:return {'ok':False,'error':str(exc)}
        except Exception:return {'ok':False,'error':'Could not save the model selection. Check Ollama and the local settings file.'}

    def due_reminders(self):
        try:return {'ok':True,'reminders':self._reminders.due()}
        except Exception:return {'ok':False,'error':'Could not check reminders. Check the local reminders database.'}

    def dismiss_reminder(self,reminder_id):
        try:return {'ok':self._reminders.finish(reminder_id,'dismissed')}
        except Exception:return {'ok':False,'error':'Could not dismiss this reminder.'}

    def choose_documents(self):
        if self._window is None:
            return {'ok':False,'reply':'The desktop window is not ready.'}
        import webview
        paths=self._window.create_file_dialog(webview.FileDialog.OPEN,allow_multiple=True,
                                             file_types=('Documents (*.txt;*.md;*.pdf;*.docx)',))
        if not paths:return {'ok':True,'reply':'No files selected.'}
        results=[]
        ok=True
        for path in paths[:50]:
            try:
                document_id=self._documents.index(path)
                results.append('Indexed document '+str(document_id)+': '+Path(path).name)
            except Exception as exc:
                ok=False
                results.append('Could not index '+Path(path).name+': '+str(exc))
        if len(paths)>50:results.append('Only the first 50 selected files were processed.');ok=False
        return {'ok':ok,'reply':'\n'.join(results)}

    def find_weather_locations(self, query):
        return self._everyday.find(query)

    def select_weather_location(self, token):
        return self._everyday.select(token)

    def get_weather_location(self):
        return self._everyday.location()

    def confirm_app_launch(self, token):
        return self._apps.confirm(token)

    def list_installed_apps(self):
        return self._apps.list_apps()

    def save_desktop_state(self, data):
        try:
            clean = self._saved.save(data)
            with self._interaction_lock:
                self._quiet_mode = clean['preferences']['quiet']
                self._speech.set_enabled(not self._quiet_mode and clean['preferences']['speechEnabled'])
                if self._quiet_mode:
                    self._handsfree_enabled = False
                    if self._voice.status().get('state') in ('listening', 'transcribing'):
                        self._voice.cancel()
            return {'ok': True}
        except (ValueError, OSError, TypeError) as exc:
            return {'ok': False, 'error': str(exc)}

def main():
    if os.name == 'nt':
        # Give this app its own taskbar identity instead of inheriting Python's.
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('Artemis.Desktop')
    parser = argparse.ArgumentParser(description='ARTEMIS Desktop V2 (WebView2)')
    parser.add_argument('--browser', action='store_true', help='Open in Chrome/Edge instead of WebView2')
    args = parser.parse_args()
    server = make_server()
    address = f'http://127.0.0.1:{server.server_port}/'
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    print('ARTEMIS Desktop V2', flush=True)
    print('Local app:', address, flush=True)
    print('Renderer:', 'default browser' if args.browser else 'Microsoft Edge WebView2', flush=True)
    try:
        if args.browser:
            webbrowser.open(address)
            print('Keep this terminal open. Ctrl+C to stop.', flush=True)
            try:
                while True: thread.join(timeout=0.5)
            except KeyboardInterrupt:
                pass
            return 0
        if os.name != 'nt':
            raise SystemExit('Native WebView2 requires Windows; use --browser for Linux/macOS testing.')
        try:
            import webview
        except ImportError as exc:
            raise SystemExit('Missing pywebview. Install with: python -m pip install pywebview') from exc
        bridge=WindowBridge()
        bridge._window=webview.create_window(
            'Artemis', url=address,
            width=1440, height=880, min_size=(260, 260),
            background_color='#070911', js_api=bridge,
            resizable=True, text_select=True, frameless=True, easy_drag=False
        )
        bridge._window.events.moved += bridge._remember_position
        # Explicitly use the renderer that passed the user's NVIDIA RTX 4060 WebGL2 test.
        # Do not fall back silently to Qt or legacy MSHTML.
        webview.start(gui='edgechromium', debug=False, private_mode=True,
                      icon=str(Path(__file__).resolve().parent / 'assets' / 'Artemis.ico'))
        return 0
    finally:
        server.shutdown()
        server.server_close()

if __name__ == '__main__': sys.exit(main())



