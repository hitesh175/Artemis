"""Artemis Desktop V1.1 — safe WebGL detection with local browser fallback."""
import argparse
import sys
import threading
import webbrowser
from pathlib import Path
from server import make_server


def main():
    parser = argparse.ArgumentParser(description="ARTEMIS Windows shell")
    parser.add_argument("--browser", action="store_true", help="Use installed browser for WebGL rendering")
    args = parser.parse_args()
    server = make_server()
    url = f"http://127.0.0.1:{server.server_port}/"
    print(f"ARTEMIS local interface: {url}")

    if args.browser:
        webbrowser.open(url)
        print("Keep this terminal open while using Artemis in your browser. Press Ctrl+C to stop.")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
        finally:
            server.server_close()
        return 0

    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        from PySide6.QtCore import QUrl
        from PySide6.QtWidgets import QApplication, QMainWindow, QMessageBox
        from PySide6.QtWebEngineWidgets import QWebEngineView
        from PySide6.QtGui import QIcon
    except ImportError as exc:
        server.shutdown()
        raise SystemExit("Qt WebEngine missing. Install PySide6 and PySide6-Addons, or run: python desktop/main.py --browser\n"+str(exc))
    app=QApplication(sys.argv[:1])
    window=QMainWindow()
    window.setWindowTitle('ARTEMIS — Private Intelligence')
    window.setWindowIcon(QIcon(str(Path(__file__).parent/'assets'/'Artemis.ico')))
    view=QWebEngineView()
    window.setCentralWidget(view)
    window.resize(1440,880)
    window.setMinimumSize(860,570)
    prompt_shown=[False]

    def verify_renderer(ok):
        if not ok or prompt_shown[0]:
            return
        def on_result(works):
            if works or prompt_shown[0]:
                return
            prompt_shown[0]=True
            msg=QMessageBox(window)
            msg.setWindowTitle('Artemis graphics compatibility')
            msg.setIcon(QMessageBox.Warning)
            msg.setText('WebGL2 is not available in the embedded Windows window.')
            msg.setInformativeText('Artemis can use your regular browser for GPU rendering without changing its backend or installing anything. The native window must remain open to keep the local service running.')
            browser_btn=msg.addButton('Open in browser', QMessageBox.AcceptRole)
            msg.addButton('Keep desktop window', QMessageBox.RejectRole)
            msg.exec()
            if msg.clickedButton() is browser_btn:
                webbrowser.open(url)
                window.showMinimized()
        view.page().runJavaScript("(function(){try{const c=document.createElement('canvas');return !!c.getContext('webgl2');}catch(e){return false;}})()", on_result)

    view.loadFinished.connect(verify_renderer)
    view.load(QUrl(url))
    window.show()
    try:
        return app.exec()
    finally:
        server.shutdown()

if __name__=='__main__':
    sys.exit(main())
