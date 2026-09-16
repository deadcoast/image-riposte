# Reading this evidence

`terminal-home`, `terminal-library`, `terminal-artwork`, `terminal-publish`, `terminal-field`, `terminal-light`, `terminal-compact` and `terminal-settings-compact` are exact-cell captures from the application's renderer. Each PNG has a matching ASCII `.txt`. The preview artwork is synthetic. `terminal-motion.gif` animates the same home material over 48 real renderer frames; it is not an animation file loaded by the application.

`terminal-session.cast` independently records the actual Rich application running in a POSIX pseudo-terminal. It can be replayed by an asciinema-compatible player. `terminal-session-report.json` identifies the read-only rehearsal and actual exit status. No source-replacement or model operation was requested in this recording.

`source-tests.txt` and `wheel-tests.txt` contain executed internal suite results. `provenance.json` and `package-equality.json` bind the baseline and installed artifacts. The final extracted-archive result is in the external release report, linked beside the release ZIP.

These files are developer evidence, not artwork-protection certification. No font binary is supplied.
