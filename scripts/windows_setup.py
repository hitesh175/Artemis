"""Guided installer engine. Fresh folders only; no changes to an existing app."""
import argparse
import hashlib
import json
import os
from pathlib import Path,PurePosixPath
import platform
import shutil
import struct
import subprocess
import sys
from urllib.request import urlopen

MARKER='artemis-setup.json'


def webview_runtime():
    if os.name!='nt':return None
    import winreg
    for hive in (winreg.HKEY_CURRENT_USER,winreg.HKEY_LOCAL_MACHINE):
        for view in (winreg.KEY_WOW64_32KEY,winreg.KEY_WOW64_64KEY):
            try:
                with winreg.OpenKey(hive,r'SOFTWARE\Microsoft\EdgeUpdate\Clients',0,winreg.KEY_READ|view) as clients:
                    for index in range(winreg.QueryInfoKey(clients)[0]):
                        try:
                            with winreg.OpenKey(clients,winreg.EnumKey(clients,index)) as key:
                                name=winreg.QueryValueEx(key,'name')[0]
                                version=winreg.QueryValueEx(key,'pv')[0]
                                if 'webview2' in str(name).lower() and str(version)!='0.0.0.0':return str(version)
                        except OSError:continue
            except OSError:continue
    return None


def readiness(target):
    runtime=webview_runtime()
    models=[];ollama=False
    try:
        with urlopen('http://127.0.0.1:11434/api/tags',timeout=2) as response:data=json.load(response)
        models=[m['name'] for m in data.get('models',[]) if isinstance(m,dict) and isinstance(m.get('name'),str)]
        ollama=True
    except Exception:pass
    target=Path(target)
    voices=target/'models'/'kokoro'
    return {'windows_x64':os.name=='nt' and struct.calcsize('P')==8 and platform.machine().upper() in ('AMD64','X86_64'),
            'python':platform.python_version(),'webview2_version':runtime,'ollama_reachable':ollama,
            'artemis_model_present':any(name in ('artemis','artemis:latest') for name in models),
            'kokoro_files_present':all((voices/name).is_file() for name in ('kokoro-v1.0.onnx','voices-v1.0.bin'))}


def verify_source(source):
    source=Path(source).resolve(strict=True)
    manifest_file=source/'MANIFEST.json'
    manifest=json.loads(manifest_file.read_text(encoding='utf-8-sig'))
    required={'app/Artemis.pyw','app/run_logged.py','app/desktop/main.py','requirements-runtime.lock','setup/FIRST_RUN.md','setup/Modelfile',
              'setup/download-whisper.py','setup/check-setup.py','scripts/windows_setup.py'}
    if not isinstance(manifest,dict) or not required.issubset(manifest):raise ValueError('Incomplete release manifest. Extract the complete source ZIP.')
    for name,digest in manifest.items():
        relative=PurePosixPath(name)
        if relative.is_absolute() or '..' in relative.parts or '\\' in name or ':' in name:
            raise ValueError('Unsafe release path.')
        path=(source/name).resolve(strict=True)
        if not path.is_relative_to(source) or not path.is_file():raise ValueError('Release file is outside its source folder.')
        if hashlib.sha256(path.read_bytes()).hexdigest()!=digest:raise ValueError('Release integrity check failed: '+name)
    return manifest,hashlib.sha256(manifest_file.read_bytes()).hexdigest()


def install(source,target,resume=False,runner=subprocess.run):
    if (os.name!='nt' or sys.version_info[:2]!=(3,11) or struct.calcsize('P')!=8
            or platform.machine().upper() not in ('AMD64','X86_64')):
        raise RuntimeError('Use Windows x64 with Python 3.11 x64 for this release.')
    source=Path(source).resolve(strict=True);target=Path(target).resolve()
    manifest,release=verify_source(source)
    if source==target or source.is_relative_to(target) or target.is_relative_to(source):
        raise ValueError('Choose a new installation folder outside the extracted release.')
    marker=target/MARKER
    if target.exists():
        if not resume or not marker.is_file():raise ValueError('The destination already exists. Choose a new folder; existing apps are never overwritten.')
        saved=json.loads(marker.read_text(encoding='utf-8'))
        if saved.get('release')!=release or saved.get('state')=='complete':
            raise ValueError('Resume only an incomplete installation of this same release.')
    elif resume:raise ValueError('There is no incomplete installation to resume.')
    if shutil.disk_usage(target.parent if target.parent.exists() else source).free<2*1024**3:
        raise ValueError('At least 2 GB of free space is needed for application packages. Models require additional space.')
    target.mkdir(parents=True,exist_ok=True)
    status={'state':'installing','release':release,'target':str(target)}
    def write():marker.write_text(json.dumps(status,indent=2),encoding='utf-8')
    write()
    try:
        for name in manifest:
            relative=PurePosixPath(name)
            if relative.parts[0]=='app':destination=target/Path(*relative.parts[1:])
            elif name.startswith('setup/') or name=='scripts/windows_setup.py':
                destination=target/'setup'/relative.name
            elif name=='requirements-runtime.lock':destination=target/relative.name
            else:continue
            destination=destination.resolve()
            if not destination.is_relative_to(target):raise ValueError('Unsafe installation path.')
            destination.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(source/name,destination)
            if hashlib.sha256(destination.read_bytes()).hexdigest()!=manifest[name]:raise ValueError('Copy verification failed: '+name)
        shutil.copy2(target/'setup'/'Modelfile',target/'Modelfile')
        shutil.copy2(target/'setup'/'FIRST_RUN.md',target/'FIRST_RUN.md')
        print('Creating the private Python environment...',flush=True)
        python=target/'.venv'/'Scripts'/'python.exe'
        if not python.is_file():runner([sys.executable,'-m','venv',str(target/'.venv')],check=True)
        print('Installing application packages. Internet access may be required...',flush=True)
        runner([str(python),'-m','pip','install','--disable-pip-version-check','--prefer-binary','-r',str(target/'requirements-runtime.lock')],check=True)
        runner([str(python),'-m','pip','check'],check=True)
        status.update(state='complete',readiness=readiness(target))
        write()
        print('Application files and Python packages installed. Read FIRST_RUN.md for runtime/model setup.',flush=True)
        return status
    except Exception as exc:
        status.update(state='failed',error=str(exc));write()
        raise


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--source-root',type=Path,default=Path(__file__).resolve().parents[1])
    parser.add_argument('--target',type=Path,required=True)
    parser.add_argument('--check',action='store_true')
    parser.add_argument('--resume',action='store_true')
    args=parser.parse_args()
    if args.check:
        verify_source(args.source_root)
        print(json.dumps(readiness(args.target),indent=2));return
    print(json.dumps(install(args.source_root,args.target,args.resume),indent=2))

if __name__=='__main__':
    try:main()
    except Exception as exc:print('SETUP FAILED: '+str(exc),file=sys.stderr);sys.exit(1)
