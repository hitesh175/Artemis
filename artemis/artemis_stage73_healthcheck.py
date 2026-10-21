"""ARTEMIS Stage 7.3: read-only regression diagnostics.
Put this file in the existing artemis/ folder and run from the project root.
Does NOT launch apps, access the microphone, or speak.
"""
from pathlib import Path
import sys, os, importlib, urllib.request, json, time
from dataclasses import dataclass
root = Path(__file__).resolve().parent.parent
sys.path.insert(0,str(root))
sys.path.insert(0,str(Path(__file__).resolve().parent))
from artemis_app_resolver_723 import Candidate, match_app, parse_open_request, discover_apps

def report(label, ok, detail=""):
    print(("[PASS]" if ok else "[CHECK]"),label,("| "+str(detail) if detail else ""))
    return bool(ok)

def run():
    good=0; total=0
    def check(label, status, detail=""):
        nonlocal good,total
        total+=1
        good+=report(label,status,detail)
    checks = [
        ("Open Spotify", "Spotify"),
        ("Could you please open Discord?", "Discord"),
        ("Here are the mess. Open Spotify.", "Spotify"),
        ("OpenSpartify", "Spartify"),
        ("How do I open Spotify?", None),
        ("Can you explain how to open Discord?", None),
        ("I'm bored today", None),
    ]
    for heard, expected in checks:
        got=parse_open_request(heard)
        check(f'Router: {heard!r}',got==expected,f'{got!r} (expected {expected!r})')
    fake=[Candidate("Spotify",Path("spotify.lnk")),Candidate("Discord",Path("discord.lnk")),
          Candidate("Notepad",Path("notepad.lnk"))]
    for raw,kind,app in [("Spotify","exact","Spotify"),("Discord","exact","Discord"),
                          ("Spartify","confirm","Spotify")]:
        m=match_app(raw,fake)
        check("Match: "+raw,m.kind==kind and m.app is not None and m.app.name==app,
              f"{m.kind}, {m.app.name if m.app else '-'}, {m.score:.2f}")
    t=time.monotonic()
    try:
        apps=discover_apps()
        check("Windows app discovery",len(apps)>0,f"{len(apps)} apps found in {time.monotonic()-t:.1f}s")
        for nm in ("Spotify","Discord"):
            m=match_app(nm,apps)
            check("Installed "+nm,m.kind!="unknown",
                  f"{m.kind}: {m.app.name if m.app else 'not found'}")
    except Exception as exc:
        check("Windows app discovery",False,repr(exc))
    try:
        import sounddevice as sd
        dev=sd.query_devices(kind="output")
        check("Audio output device",bool(dev),dev.get("name") if dev else "none")
    except Exception as exc:
        check("Audio output device",False,repr(exc))
    try:
        from artemis.voice import Speaker
        check("Piper voice module",True,str(Path(importlib.import_module("artemis.voice").__file__)))
    except Exception as exc:
        check("Piper voice module",False,repr(exc))
    try:
        with urllib.request.urlopen("http://127.0.0.1:11434/api/tags",timeout=4) as r:
            tags=json.load(r)
        models=[m.get('name','') for m in tags.get('models',[])]
        check("Ollama model 'artemis'",any(m.split(':')[0]=="artemis" for m in models),
              "Models: "+", ".join(models))
    except Exception as exc:
        check("Ollama service",False,repr(exc))
    print(f"\nResult: {good}/{total} checks passed.")
    print("This test does not execute application commands or play speech.")
    print("If checks fail, share the terminal output before replacing working files.")
if __name__=="__main__":
    run()
