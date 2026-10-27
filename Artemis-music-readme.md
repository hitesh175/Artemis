# Artemis guest music playback in Brave

Restart Artemis after updating. Enable spoken replies and hands-free with Quiet off.

- “Play music on YouTube” → Artemis asks for a genre, artist or song.
- Answer “jazz”, an artist or a song name → Artemis selects the first regular YouTube video result and starts playback.
- “Play jazz on YouTube” starts a specific search immediately.
- “Pause music”, “resume music” and “stop music” control the Artemis music window.
- “Cancel” abandons the follow-up question. It also expires after two minutes.

The installed Brave browser starts a dedicated music window. Artemis connects to that window's loopback DevTools endpoint. Guest consent/session state persists under data/music-brave, separately from the ordinary Brave profile. No login is requested by Artemis; public videos can play as a guest. YouTube may still restrict individual videos or require verification. Artemis does not bypass those restrictions and reports playback failure honestly. YouTube may show ads.

Requires Brave and Python playwright (already installed for this update). No additional browser download is required. Searches are sent to YouTube. No music files are downloaded. A muted live test confirmed guest playback, pause, resume, stop and browser shutdown without sign-in. The earlier controlled-browser test failure was resolved by launching installed Brave normally before connecting to its local control endpoint.

Hands-free remains opt-in; use headphones if speaker audio is picked up by the microphone. Acoustic echo cancellation is not implemented. Closing Artemis closes its dedicated music browser.

Rollback: restore desktop/music.py from ui-backups/before-guest-music-* and restart Artemis. Other app code, models and saved conversations are unchanged.
