"""Verify source distribution contents, hashes, privacy exclusions and reproducibility."""
import hashlib
import argparse
import json
from pathlib import Path,PurePosixPath
import zipfile
import build as source_build

ROOT=Path(__file__).resolve().parents[1]
FORBIDDEN={'data','logs','models','voice_test','.venv','__pycache__','.git'}

def verify(installed_root=None):
    archive=source_build.build()
    first=hashlib.sha256(archive.read_bytes()).hexdigest()
    source_build.build()
    assert hashlib.sha256(archive.read_bytes()).hexdigest()==first,'Source bundle is not reproducible'
    with zipfile.ZipFile(archive) as package:
        names=package.namelist()
        assert len(names)==len(set(names)),'Duplicate archive paths'
        manifest=json.loads(package.read('MANIFEST.json'))
        assert set(names)==set(manifest)|{'MANIFEST.json'},'Manifest does not describe every payload file'
        for name,digest in manifest.items():
            relative=PurePosixPath(name)
            assert not relative.is_absolute() and '..' not in relative.parts,'Unsafe archive path'
            assert not FORBIDDEN.intersection(relative.parts),'Private/runtime directory included'
            assert not name.endswith(('.sqlite3','.pyc','.log')),'Runtime file included'
            assert hashlib.sha256(package.read(name)).hexdigest()==digest,'Payload hash mismatch: '+name
            assert hashlib.sha256((ROOT/name).read_bytes()).hexdigest()==digest,'Stale payload: '+name
        required={'scripts/install-local.ps1','scripts/rollback-local.ps1','requirements.txt','README.md','app/Artemis.pyw'}
        assert required.issubset(names),'Installation/rollback instructions or scripts missing'
    result={'passed':True,'kind':'source distribution, not a standalone installer','files':len(manifest),
            'sha256':first,'archive':str(archive),'reproducible':True,'runtime_data_excluded':True}
    if installed_root is not None:
        installed_root=Path(installed_root).resolve(strict=True)
        checked=0
        for name,digest in manifest.items():
            if name.startswith('app/'):
                target=installed_root/Path(name).relative_to('app')
                assert target.is_file(),'Installed file missing: '+name
                assert hashlib.sha256(target.read_bytes()).hexdigest()==digest,'Installed file differs: '+name
                checked+=1
        result['installed_files_verified']=checked
    (ROOT/'output'/'release-verification.json').write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--installed-root',type=Path)
    verify(parser.parse_args().installed_root)
