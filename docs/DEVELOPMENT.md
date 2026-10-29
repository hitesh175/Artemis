# Development

[Project overview](../README.md) · [Architecture](../ARCHITECTURE.md) · [Setup](../setup/FIRST_RUN.md)

## Source structure

```text
app/                  Desktop application source
  artemis/            Speech engine and app resolver
  desktop/            Python services and native bridge
    web/              HTML, CSS, and JavaScript interface
docs/                 Usage, development, screenshots, historical notes
scripts/              Checks, source build, guided setup, local maintenance
setup/                First-run instructions and explicit model preparation
tests/                Python and JavaScript regression checks
```

Make application changes in `app/`. The installed application is a separate copy; editing the repository does not automatically update it. Personal data and models are excluded from version control.

## Local environment

Use Python 3.11 x64 on Windows and Node.js for JavaScript checks. Node.js is not an application runtime dependency.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements-runtime.lock
.\.venv\Scripts\python.exe scripts/check.py
```

`requirements-runtime.lock` pins the direct runtime packages used in the tested setup. Transitive packages are resolved by pip; it is not a complete hash lock. `requirements.txt` provides broader development ranges. `requirements-baseline.lock` records an older environment, including removed experiments; do not use it as the installation requirements.

## Run a development copy

```powershell
.\.venv\Scripts\python.exe app/run_logged.py
```

Prepare Ollama, WebView2, and model files as described in the setup guide. The development copy uses its own `app/data/` and `app/logs/`. Place Kokoro files under `app/models/kokoro/` or set `ARTEMIS_KOKORO_DIR`. Close other Artemis instances before testing voice devices.

Fresh settings start in Quiet mode. Model downloads, microphone capture, and audio output should remain explicit during testing.

## Verification

`scripts/check.py` parses Python source, runs regression tests, and checks JavaScript. It uses mocks/synthetic audio; it does not start microphone capture or audible playback.

Native installed-app checks are separate:

- `scripts/verify-fresh-install.py --root PATH` checks an installation with temporary data. `--visible` also checks frame-based updates in a visible window.
- `scripts/verify-installed.py` checks the original development installation, including cached voice loading and real local-model chat. `--skip-voice-warmup` limits it to UI/tool/chat checks.
- `scripts/check-real-use.py` checks selected local-model answers and an in-memory speech round trip. It does not record or play audio.

Some installed-app maintenance scripts retain the original developer's installation path. Review or adapt it before running them on another computer. The general Windows installer and `verify-fresh-install.py --root` accept an explicit destination.

For documentation screenshots, `verify-fresh-install.py --root app --review-settings --review-width 520`
keeps an isolated preview open until closed. Choose `--review-section appearance`,
`briefings`, `models`, or `chat`. The chat preview saves an example fact in temporary
memory and sends a sample question to the local Ollama model. It never records or
plays audio, and its temporary state is removed after the preview closes.

## Build and inspect the source distribution

```powershell
.\.venv\Scripts\python.exe scripts/build.py
.\.venv\Scripts\python.exe scripts/verify-release.py
```

The output is `output/releases/artemis-source.zip`. It contains current source, documentation, tests, setup scripts, and a file-hash manifest. Release verification builds twice, checks identical archive hashes and exact manifest coverage, and rejects private/runtime directories.

To compare a known installed copy as well:

```powershell
.\.venv\Scripts\python.exe scripts/verify-release.py --installed-root "C:\path\to\Artemis"
```

The bundle is a source distribution with guided online setup, rather than a standalone/offline executable installer. The [first-run guide](../setup/FIRST_RUN.md) covers its intended installation flow.

## Local updates and cleanup

`scripts/install-local.ps1` updates an existing developer installation, verifies file hashes, and keeps a rollback snapshot. It is separate from `install-windows.ps1`, which installs into a new folder. `rollback-local.ps1` restores a selected supported snapshot; it does not undo dependency changes.

`scripts/cleanup-artifacts.ps1` previews a fixed list of known historical build/test leftovers. `-Apply` deletes those paths, and `-IncludeInstalledBackups` retains only the latest matching rollback backup. Review the report and destination first. Active data, model files, and the private Python environment are outside its deletion list.

## Contribution boundaries

- Preserve explicit confirmation for reviewed plans and ambiguous app launches.
- Keep recordings, speech, model downloads, and scheduled briefings opt-in.
- Treat saved facts, documents, and model replies as data rather than executable instructions.
- Do not copy source, artwork, or documentation from OpenJarvis; it is an ideas-only reference.
- Use invented data in tests and redact personal information in reports/screenshots.
- Keep dependency/model attribution and validation claims accurate.

The [development history](DEVELOPMENT_HISTORY.md) preserves earlier implementation details. Its superseded paths and statements are historical context, not current setup instructions.
