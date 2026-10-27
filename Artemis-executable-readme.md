# Artemis Windows executable

Double-click Artemis.exe, or use the Artemis desktop/Start menu shortcut.

This is a native Windows launcher for the existing Artemis installation. It starts the working desktop assistant without a console window and uses the Artemis icon. It preserves the existing single-instance guard, crash logs, speech engines, settings and chat history.

Keep Artemis.exe inside `C:\Users\kanag\Desktop\Artemis`. It depends on that folder's `.venv`, Python application files, models and assets. It is not a self-contained application or an installer for another computer. Copying only this executable to a different computer will not install Artemis. Ollama with the artemis model and Microsoft Edge WebView2 must remain available.

The executable first looks beside itself for Artemis.pyw and the Python environment, then checks the current user's Desktop/Artemis folder. `Artemis.exe --check` validates those paths without starting the interface or audio.

Rollback: the installation creates a dated `ui-backups/before-native-exe-*` folder containing prior shortcuts and any previous Artemis.exe. Your existing Python entry point and fallback start_artemis_v2.bat remain usable. No application source or AI model is modified by this package.

Launcher.cs is included as the executable's source code. This build is unsigned.
