"""One-time HTTPS model installation. ARTEMIS runtime remains offline."""
import argparse
import urllib.request
from zipfile import ZipFile

from artemis.config import PROJECT_ROOT, VOSK_PATH

VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-en-us-0.15.zip"


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--include-jarvis", action="store_true",
                        help="Also download the OPTIONAL trained Hey Jarvis backup model")
    args = parser.parse_args()

    if not VOSK_PATH.is_dir():
        folder = PROJECT_ROOT / "models"
        folder.mkdir(exist_ok=True)
        archive_path = folder / "vosk_model_download.zip"
        print("Downloading the Vosk English model (one time, over HTTPS)...")
        urllib.request.urlretrieve(VOSK_URL, archive_path)
        try:
            with ZipFile(archive_path) as archive:
                root = folder.resolve()
                for member in archive.infolist():
                    dest = (folder / member.filename).resolve()
                    if not dest.is_relative_to(root):
                        raise RuntimeError("Archive contains an unsafe path")
                archive.extractall(folder)
        finally:
            archive_path.unlink(missing_ok=True)
        if not VOSK_PATH.is_dir():
            raise RuntimeError("Vosk model extraction failed")
    else:
        print("Vosk model already available:", VOSK_PATH)

    if args.include_jarvis:
        import openwakeword.utils
        print("Downloading optional trained 'Hey Jarvis' backup wake model...")
        openwakeword.utils.download_models(model_names=["hey_jarvis"])

    print("Done. Offline Artemis wake phrase mode is ready for Windows testing.")


if __name__ == "__main__":
    main()
