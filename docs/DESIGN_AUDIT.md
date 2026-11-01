# Artemis interface audit

Date: 1 November 2026. Source baseline: `24cbf4f`.

## Resolution — 1 November 2026

**All seven findings below have been addressed in the application source.** The
original findings and 11/20 baseline are retained as historical evidence.

| Finding | Resolution and verification |
| --- | --- |
| Panel focus | Labelled dialogs move focus inside, keep Tab inside, make background controls inert, and restore the opener. Native checks pass. Compact Chat keeps native layout controls accessible. |
| Small-window clipping | Header and home content adapt; essential controls pass at 260×260, 320×480, 500×640, 800×600 and normal desktop sizes. |
| Placeholder contrast | Shared placeholder colour `#9fb2c8` replaces the browser grey; native computed-style check passes against the dark field. |
| Small functional labels | Status, header controls, Mini controls, and persistence labels use a 12 px metadata floor. Body/chat and settings help use 14 px. |
| Settings navigation | Six categories contain all 17 original groups, each mapped exactly once. The chooser stays above the content. |
| Reply announcements | Separate polite region announces completed replies. Streaming and restored history stay quiet. Native calculation check verifies the announcement and cleared busy state. |
| Overlapping styles | One active `theme.css` replaces seven historical theme layers. Shared tokens and `DESIGN.md` describe the palette, type, layout, and component behavior. |

Final rendered General Settings scan: **zero detector findings**. Final source scan:
one contextual copy warning about concise privacy limitations; those factual
boundaries were intentionally retained. No small-text or low-contrast finding
remains in these scanned states. This does not establish full WCAG conformance.

The native Mini → Chat → Full round trip and the full Python/JavaScript regression
suite pass. Updated lossless screenshots are in `docs/images/`.

Performance comparison on the isolated preview: 12 panel samples were about
7–14 ms before and 8–14 ms afterward, measured from the open call through two
animation frames, **not** through completion of the panel's transition. A burst of
500 text fragments still coalesces to one DOM paint (about 7 ms in this check).
No substantial lag was reproduced, so no hardware-wide speed improvement is claimed.
Screen-reader listening, touch hardware, broader zoom settings, and slow-PC profiling
remain additional validation rather than demonstrated outcomes of this run.

The sections below describe the original audit and should not be read as unresolved
defects in the updated interface.

Method: Impeccable 4.8.0 technical audit, source inspection, and direct inspection of
an isolated native WebView2 preview. This is an audit, not a redesign or a benchmark.
The ratings below are reviewer assessments using Impeccable's rubric; they are not
an automated certification or a WCAG conformance claim.

## Implementation integrity verdict

**Pass for product identity; significant usability work remains.** The lunar emblem,
midnight palette, distinct user/assistant messages, and visible Quiet controls form
a coherent Artemis interface. The priority problems concern access and navigation,
not a need to replace that identity. Detector style preferences are not treated as
product requirements.

## Health score

| Dimension | Score | Main evidence |
| --- | --- | --- |
| Accessibility | 2/4 | Panel focus escapes to the obscured background; placeholder contrast warning; small functional text. |
| Performance | 3/4 | Streaming updates are batched; panel decoration pauses; hardware-dependent lag remains unprofiled. |
| Theming | 1/4 | Some tokens exist, but most styling uses literal colours across numerous override layers. |
| Responsive design | 2/4 | Tested controls fit at 500 px and above; full view clips controls at narrower permitted sizes. |
| Implementation integrity | 3/4 | Consistent identity and native controls; long Settings navigation and overlapping style layers need refinement. |
| **Total** | **11/20** | **Acceptable under the rubric; significant work needed.** |

Seven consolidated issues: **0 P0, 3 P1, 4 P2, 0 P3**. Raw detector warnings are
not seven separate verified defects; duplicated and contextual warnings were reviewed.

## Priority findings

### 1. [P1] Settings does not manage keyboard focus as an overlay

- Location: `app/desktop/web/app.js:14` and `:15`; panel markup in `index.html`.
- Category: accessibility.
- Opening Settings through its button leaves focus on `settings-open`, behind the
  dimming overlay. From the Settings close button, Shift+Tab moves to the obscured
  fullscreen button (`expand-button`). Closing the panel with an internal control
  focused leaves focus on `BODY` rather than restoring the opener.
- Impact: keyboard users can lose their position and reach obscured controls. The
  panel behaves visually as a modal without corresponding keyboard behavior.
- Relevant checks: WCAG 2.4.3 focus order and dialog interaction conventions. A
  screen-reader conformance assessment has not been performed.
- Fix: move focus into the opened panel; keep navigation within its intended
  interaction area; make the underlying app controls inert while preserving native
  window controls where appropriate; restore the actual opener on close. Preserve
  Escape, Ctrl+K, Mini mode, and existing confirmations.
- Suggested command: `$impeccable harden`.

### 2. [P1] Full view can shrink until important controls are clipped

- Location: `app/desktop/main.py:455`; `styles.css:1`, `mini.css:28`, and
  `window-chrome.css:6` for layout and overflow rules.
- Category: responsive design and accessibility.
- CDP viewport tests: key controls fit at 1100×800, 800×600, 500×640, and
  1100×600 CSS pixels. At 320×480, Settings and Quiet mode extend outside the
  viewport. At 260×260, Chat, microphone, speech, Settings, and Quiet controls are
  clipped. The native window currently permits a minimum of 260×260.
- Impact: users can resize the full interface into a state with inaccessible
  controls; hidden page overflow prevents recovery through ordinary scrolling.
- Relevant check: WCAG 1.4.10 reflow; the width-320 result is a concrete warning,
  not a complete zoom or conformance test.
- Fix: introduce a compact header and usable small-height layout, or enforce an
  appropriate full-view minimum while allowing the separate Mini layout to stay
  small. Check panel scrolling and Windows display scaling after the change.
- Suggested command: `$impeccable adapt`.

### 3. [P1] Weather placeholder contrast falls below the normal-text target

- Location: `app/desktop/web/settings.css:17`; `index.html` field `weather-city`.
- Category: accessibility.
- The rendered detector reports approximately **3.8:1** for the default placeholder
  `City, country`: `#757575` on `#0b192b`, below the 4.5:1 normal-text AA target.
  Settings supplies an explicit field background but no explicit placeholder colour.
- Impact: the input's formatting hint is harder to read than the adjacent label.
- Relevant check: WCAG 1.4.3 contrast for meaningful placeholder text.
- Fix: specify a placeholder token with sufficient contrast; check normal, focus,
  disabled, and error states separately rather than brightening every muted label.
- Suggested command: `$impeccable harden`.

### 4. [P2] Important status and control labels are too small

- Location: `premium.css:6`, `:17`, `:23`, `:25`; `quiet.css:1`, `:4`;
  `mini.css:7`, `:16`; `window-chrome.css:2`.
- Category: accessibility and responsive design.
- Rendered examples include 10 px Hands-free, Mini, and Quiet buttons; 10 px
  persistence status; and 8 px READY and LOCAL OLLAMA labels. At narrow sizes,
  header controls reduce further to 9 px and wrap over multiple lines.
- Impact: basic states are harder to scan, especially at high display density.
- There is no absolute WCAG minimum font size. Impeccable's small-text floor is
  a design-quality heuristic, not proof of a standards violation.
- Fix: adopt a readable functional type scale, testing around 12–14 px for controls
  and metadata; keep larger body text and preserve the existing Segoe UI identity.
- Suggested commands: `$impeccable typeset`, then `$impeccable adapt`.

### 5. [P2] Settings navigation requires excessive scrolling

- Location: `index.html`'s 17 `.settings-section` groups; `settings.css:3`.
- Category: implementation integrity and navigation.
- At the measured 979×687 CSS-pixel viewport, Settings content is 3539 px tall
  inside a 546 px scroll area: approximately **6.5 panel heights**. Model selection
  and service status sit near the end, after everyday commands and help sections.
- Impact: recurring settings are slow to find. Many independent features share one
  undifferentiated scroll path.
- Fix: group existing controls into a few named categories with visible navigation
  or search. Keep all features, clear service/error states, and the current command
  details; prioritise frequently used preferences over lengthy help text.
- Suggested commands: `$impeccable layout`, then `$impeccable clarify`.

### 6. [P2] Chat lacks an explicit announcement strategy for new replies

- Location: `index.html`'s `#messages`; `app.js` message creation and
  `chat-renderer.js:8` streaming paint.
- Category: accessibility.
- `#messages` has no `role="log"` or live-region attribute. The persistence status
  has `role="status"`, but that communicates saving rather than the assistant reply.
- Impact: users of assistive technology may not be notified reliably when a reply
  completes. Actual screen-reader behavior still needs testing.
- Relevant checks: WCAG 4.1.3 status messages and appropriate chat-log semantics.
- Fix: design and test one polite announcement per completed reply, with a clear
  busy/finished state. Do not announce each streamed token or replay restored history.
- Suggested command: `$impeccable harden`.

### 7. [P2] Styling depends heavily on overlapping literal values

- Location: the stylesheet list in `index.html:1`; `styles.css`, `premium.css`,
  `antimatter.css`, `lunar.css`, `artemis-identity.css`, and `settings.css`.
- Category: theming and maintenance.
- The page loads 19 stylesheets. Several redefine the same header, emblem, panel,
  colour, and spacing selectors. There are some useful variables, but most colours
  remain hard-coded. The complete web directory has about 52 KB of CSS and 73 KB of
  JavaScript, so file count alone is not evidence of a large download problem.
- Impact: small changes can unexpectedly inherit older values; contrast, focus,
  and responsive fixes are difficult to keep consistent.
- Fix: document the current effective palette/type/spacing values, then consolidate
  redundant overrides into shared tokens and component rules. Preserve screenshots
  during the refactor. Do not add a light theme merely to satisfy a generic rubric.
- Suggested commands: `$impeccable document`, then `$impeccable extract`.

## What already works

- The lunar identity is consistent across Home, Chat, and Settings. User and
  assistant messages are visually distinct and wrap long content.
- The chat input has a visible keyboard focus indicator in the actual cascade;
  an earlier base stylesheet's `outline:none` is overridden. This is not a defect.
- Closed panels are inert and use content visibility. Decorative SVG animation
  pauses while a panel is open; reduced-motion alternatives exist.
- Chat streaming updates are coalesced through animation frames and preserve the
  reader's scroll position. Those existing optimisations should be retained.
- Form labels, semantic buttons, disclosure controls, Quiet mode, Escape, and
  Ctrl+K provide a useful foundation.

## Detector evidence and contextual exclusions

Raw reports and PNG evidence are saved locally under `output/design-audit/`.
Source and rendered results overlap and should not be added as unique defects.

- Source scan: 19 warnings, including active and inactive styling.
- Rendered Settings: 28 warnings, including 17 repeated “nested cards” warnings.
- Rendered Chat: 11 warnings, chiefly small labels and a header kicker.
- The `overused-font: Inter` source warning is overridden by `premium.css`'s Segoe
  UI family. Replacing the current font because of that warning is not warranted.
- Source contrast warnings in `mini.html` describe the older standalone file.
  The current Mini bridge changes the layout of the main page rather than loading
  that file, so those warnings are not assigned to the active Mini interface.
- Nested Settings groups are intentional grouping, not 17 independent bugs. Their
  navigation cost is captured in finding 5.
- Glow, “kicker above heading”, and aphoristic-copy warnings are style preferences.
  They do not justify removing Artemis's visual identity or clear privacy boundaries.
- No claim is made that every active colour passes contrast; only the investigated
  states were tested. Disabled controls and obscured background text need context.

## Performance limits and next pass

This run checked implementation patterns; it did not establish the cause of the
reported lag. GPU/CPU profiling, panel opening latency, a long real conversation,
and slower hardware remain unmeasured. Start a separate `$impeccable optimize`
pass before attributing lag to blur, the emblem, the local model, or stylesheet count.
The inactive legacy WebGL path is not evidence that the active home screen is
rendering that shader.

Recommended sequence: **harden keyboard/contrast → adapt small windows → typeset
controls → layout Settings → document/extract tokens → optimize measured lag →
polish → audit again.** All changes should preserve the app's existing features.

## Run notes

The installed skill and its context launcher were read; no product/design context
files existed. Impeccable explicitly allowed this scoped review of the existing
implementation. No UI files were edited and no automatic design hook was installed.
The source and rendered detector ran successfully and returned findings. There was
no browser overlay or separate live server; desktop scans attached directly to an
isolated WebView2 instance at `127.0.0.1:9222`. Screenshots used lossless CDP PNG
capture. Small-window checks used CDP viewport emulation, not physical touch input
or a physical monitor change. Voice stayed silent; sample chat used local arithmetic.
No screen reader, live microphone, real voice playback, high-contrast theme, or
comprehensive 200% text/zoom test was run. The preview and its temporary data were
closed and removed after the audit; evidence files were retained locally.

You can ask for these fixes one at a time, together, or in another order. Re-run
`$impeccable audit` after fixes to compare the findings and reviewer score.
