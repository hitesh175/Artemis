"""Installer boundaries and recovery, without downloads or user state."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import windows_setup as setup


class SetupTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.source=self.root/'release';self.source.mkdir()
        self.target=self.root/'installed'
        names=('app/Artemis.pyw','app/run_logged.py','app/desktop/main.py',
               'requirements-runtime.lock','setup/FIRST_RUN.md','setup/Modelfile',
               'setup/download-whisper.py','setup/check-setup.py','scripts/windows_setup.py')
        self.manifest={}
        for name in names:
            path=self.source/name;path.parent.mkdir(parents=True,exist_ok=True)
            path.write_text(name,encoding='utf-8')
            self.manifest[name]=hashlib.sha256(path.read_bytes()).hexdigest()
        self.save_manifest()
        self.calls=[]
        self.ready=patch.object(setup,'readiness',return_value={'test':True})
        self.ready.start();self.addCleanup(self.ready.stop)

    def save_manifest(self):
        (self.source/'MANIFEST.json').write_text(json.dumps(self.manifest),encoding='utf-8')

    def runner(self,args,**kwargs):
        self.calls.append(args)
        if args[1:3]==['-m','venv']:
            python=Path(args[3])/'Scripts'/'python.exe'
            python.parent.mkdir(parents=True);python.touch()

    def test_fresh_install_and_complete_resume_refused(self):
        result=setup.install(self.source,self.target,runner=self.runner)
        self.assertEqual(result['state'],'complete')
        self.assertEqual((self.target/'Artemis.pyw').read_text(),'app/Artemis.pyw')
        self.assertTrue((self.target/'setup/windows_setup.py').is_file())
        self.assertFalse((self.target/'data').exists())
        self.assertEqual(len(self.calls),3)
        self.assertIn('--prefer-binary',self.calls[1])
        with self.assertRaises(ValueError):setup.install(self.source,self.target,True,self.runner)

    def test_existing_folder_preserved(self):
        self.target.mkdir();private=self.target/'private.txt';private.write_text('keep')
        for resume in (False,True):
            with self.assertRaises(ValueError):setup.install(self.source,self.target,resume,self.runner)
        self.assertEqual(private.read_text(),'keep');self.assertEqual(self.calls,[])

    def test_tamper_and_escape_refused_before_destination_created(self):
        (self.source/'app/Artemis.pyw').write_text('changed')
        with self.assertRaises(ValueError):setup.install(self.source,self.target,runner=self.runner)
        self.assertFalse(self.target.exists())
        (self.source/'app/Artemis.pyw').write_text('app/Artemis.pyw')
        self.manifest['../outside']='bad';self.save_manifest()
        with self.assertRaises(ValueError):setup.verify_source(self.source)

    def test_failed_install_can_resume_same_release(self):
        def fail(args,**kwargs):raise RuntimeError('simulated package failure')
        with self.assertRaises(RuntimeError):setup.install(self.source,self.target,runner=fail)
        self.assertEqual(json.loads((self.target/setup.MARKER).read_text())['state'],'failed')
        self.assertEqual(setup.install(self.source,self.target,True,self.runner)['state'],'complete')

    def test_resume_different_release_refused(self):
        self.target.mkdir()
        (self.target/setup.MARKER).write_text(json.dumps({'state':'failed','release':'other'}))
        with self.assertRaises(ValueError):setup.install(self.source,self.target,True,self.runner)

    def test_destination_inside_release_refused(self):
        with self.assertRaises(ValueError):setup.install(self.source,self.source/'nested',runner=self.runner)


if __name__=='__main__':unittest.main()
