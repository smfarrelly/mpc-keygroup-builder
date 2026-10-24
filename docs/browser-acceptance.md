# Browser acceptance boundary

The local home page and archive index have automated static tests for escaped
untrusted text, no external assets/inline event handlers, restrictive content
security policies, document language, viewport metadata, a main landmark, and
basic selected-palette contrast. Archive search code is separate from archive
data; the home page requires no JavaScript.

These tests do not substitute for opening the generated pages in a browser.
The current agent browser tool rejects local `file:` URLs, so live visual and
runtime acceptance is still unverified. Do not serve or upload private reports
merely to work around that restriction.

When a person can open the HTML locally, use this short checklist:

1. Read it at a narrow window width and 200% zoom. Long paths and commands should
   wrap without hiding controls or forcing the main content off screen.
2. Navigate with Tab and Shift+Tab. Focus should remain visible. Follow section
   links and open/close native details disclosures using the keyboard.
3. Confirm that absent inputs say not selected/not checked, and that historical
   hardware passes are separate from current file availability.
4. In the archive index, search by a project name and a note, then search for no
   match and clear the search. Full-scan error counts must remain visible.
5. Confirm that current/stale/unknown recipe status is clearly distinguished
   from file integrity. No button should execute a shell command or modify data.
6. Reopen offline. The page should remain readable without downloading assets.

Record browser/version, platform, date, file generated, and any failed step.
This is browser-only acceptance; it does not require the MPC or change hardware
listening records. Generated reports include personal paths and notes, so keep
the observations local unless they have been sanitized for an issue report.
