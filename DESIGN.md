---
name: Artemis
description: A quiet Windows workspace for local conversation and explicit everyday tools.
colors:
  canvas: "#070d18"
  chrome: "#080f1b"
  quiet-text: "#c4e8dd"
  quiet-fill: "#15332b80"
  quiet-border: "#9ad5c647"
  idle-state: "#bad9ff"
  panel-start: "#142238"
  panel-end: "#091322"
  text: "#e9edf4"
  muted: "#aebed1"
  placeholder: "#9fb2c8"
  accent: "#bad9ef"
  gold: "#cfbea0"
  surface: "#0c1727"
  raised: "#18283c"
  field: "#0c1929"
  border: "#33465d"
  button: "#263d56"
  user-message: "#c7d3e1"
typography:
  body:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "14px"
    lineHeight: 1.7
  control:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "13px"
  metadata:
    fontFamily: "Segoe UI Variable Text, Segoe UI, sans-serif"
    fontSize: "12px"
rounded:
  component: "14px"
  control: "12px"
  field: "8px"
  dock: "22px"
  panel: "18px"
  message-tail: "4px"
  pill: "99px"
spacing:
  compact: "8px"
  group: "12px"
  section: "20px"
---

## Overview

Preserve the lunar emblem and midnight scenery. Clear controls, readable states,
and keyboard navigation take priority over decoration. The source of truth is
`app/desktop/web/theme.css`, supported by component styles.

## Colors

Use shared variables for foregrounds, surfaces, borders, focus, fields, and buttons.
Gold identifies Settings headings. Emblem state colours remain in `icon-mode.css`.
Placeholders need at least 4.5:1 contrast against the field background.

## Typography

Use native Segoe. Functional metadata starts at 12 px, controls at 13 px, and
paragraphs/chat at 14 px. Help prose wraps. Heading tracking is no tighter than -0.03em.

## Layout

Home has native window controls, a wrapping header, emblem/status, and dock. Under
650 px the header reorganises; under 420 px height decorative content yields to
essential controls. Mini and compact Chat retain native Full/Collapse controls.
Settings uses General, Voice, Daily, Tools, Knowledge, and System categories.

## Elevation & Depth

Use opaque working controls and a dimming overlay. Avoid broad backdrop blur over
panels. Pause decorative animation while panels open. Honour reduced motion.

## Shapes

Use 14 px message corners. Settings groups use spacing and a fine rule, without
nested cards. The rounded dock and header controls retain the Artemis identity.

## Components

Full-view dialogs manage initial focus, keyboard boundaries, background inertness,
Escape, and opener restoration. Compact Chat is a region with native-layout controls.
Chat announces completed replies once; streaming tokens and history are not replayed.
Preserve Stop reply, Stop speaking, and all action confirmations.

## Do's and Don'ts

- Check 260×260, 320×480, 500×640, and normal desktop sizes.
- Modify active styles instead of loading historical theme experiments.
- Keep recording/playback explicit; use temporary data and Quiet mode for tests.
- Measure lag before assigning a cause or claiming an improvement.
