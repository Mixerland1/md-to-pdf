import tempfile
import unittest
import zipfile
from pathlib import Path
from md_to_pdf.updater import select_release, checksum_for, unpack_windows, DOWNLOAD, WINDOWS

def release(tag, pre=False):
    return dict(tag_name=tag, prerelease=pre, draft=False, assets=[
        dict(name=n, state="uploaded", size=123, browser_download_url=DOWNLOAD+tag+"/"+n)
        for n in (WINDOWS,"SHA256SUMS.txt")])

class UpdaterTests(unittest.TestCase):
    def test_channels(self):
        releases=[release("v0.4.0b2",True),release("v0.3.2"),release("v0.4.0b1",True)]
        self.assertEqual(select_release(releases,"0.3.0",WINDOWS).version,"0.3.2")
        self.assertEqual(select_release(releases,"0.4.0b1",WINDOWS).version,"0.4.0b2")
        self.assertIsNone(select_release(releases,"0.4.0",WINDOWS))
        self.assertEqual(select_release([release("v0.4.0")],"0.4.0b2",WINDOWS).version,"0.4.0")
    def test_exact_asset_and_checksum(self):
        r=release("v0.4.1")
        r["assets"][0]["browser_download_url"]="https://example.org/wrong.zip"
        self.assertIsNone(select_release([r],"0.4.0",WINDOWS))
        self.assertEqual(checksum_for("a"*64+"  "+WINDOWS,WINDOWS),"a"*64)
        with self.assertRaises(ValueError):
            checksum_for("bad  "+WINDOWS,WINDOWS)
    def test_extract(self):
        with tempfile.TemporaryDirectory() as d:
            root=Path(d)
            archive=root/"release.zip"
            with zipfile.ZipFile(archive,"w") as z:
                z.writestr("MD-to-PDF/MD-to-PDF.exe","new")
                z.writestr("MD-to-PDF/_internal/lib.dll","lib")
                z.writestr("MD-to-PDF/README.md","ignore")
            unpack_windows(archive,root/"out")
            self.assertEqual((root/"out/MD-to-PDF.exe").read_text(),"new")
            self.assertFalse((root/"out/README.md").exists())
            with zipfile.ZipFile(archive,"a") as z:
                z.writestr("MD-to-PDF/_internal/../../escape","bad")
            with self.assertRaises(ValueError):
                unpack_windows(archive,root/"other")
            self.assertFalse((root/"escape").exists())

    def test_installer_asset_selection(self):
        from md_to_pdf.updater import WINDOWS_SETUP
        r=release("v0.4.0b14",True)
        self.assertIsNone(select_release([r],"0.4.0b13",WINDOWS_SETUP))
        r["assets"].append(dict(name=WINDOWS_SETUP,state="uploaded",size=123,
                                browser_download_url=DOWNLOAD+r["tag_name"]+"/"+WINDOWS_SETUP))
        self.assertEqual(select_release([r],"0.4.0b13",WINDOWS_SETUP).asset,WINDOWS_SETUP)

    def test_restart_environment_discards_stale_bundle_state(self):
        from unittest.mock import patch
        from md_to_pdf.updater import restart_environment
        import os,sys
        with tempfile.TemporaryDirectory() as folder:
            bundle=Path(folder)/"_internal"
            with patch.object(sys,"_MEIPASS",str(bundle),create=True), patch.dict(os.environ,{"_PYI_APPLICATION_HOME_DIR":"old","WEASYPRINT_DLL_DIRECTORIES":"old","PATH":str(bundle/"native")+os.pathsep+str(Path(folder)/"bin")},clear=True):
                env=restart_environment()
            self.assertNotIn("_PYI_APPLICATION_HOME_DIR",env)
            self.assertNotIn("WEASYPRINT_DLL_DIRECTORIES",env)
            self.assertEqual(env["PYINSTALLER_RESET_ENVIRONMENT"],"1")
            self.assertEqual(env["PATH"],str(Path(folder)/"bin"))
