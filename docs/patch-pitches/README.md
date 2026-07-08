# Patch Pitch Review Folder

This folder collects scenario-by-scenario pitch docs for tightening the
benchmark into a more uniform research-paper artifact.

## Goal

Make `S1-S9` more comparable without making them easier. The intended direction
is:

- keep the same five vulnerability families per scenario
- remove duplicate or accidental shortcut solve paths
- make each flag measure a more distinct capability
- preserve framework-specific flavor
- preserve or slightly increase overall difficulty

## Common Normalization Themes

- Prefer low-privilege escalation over fully public admin reads for access
  control flags.
- Prefer one intended debug/config leak over multiple public leak paths.
- Force weak-hash flags to require leak-plus-crack-plus-pivot, rather than
  allowing direct default-credential guesses.
- Align SQLi flags around similar preconditions, especially whether they require
  authentication.
- Keep login/token weaknesses framework-native, but avoid letting one scenario
  have a much richer auth exploit than the rest unless that is intentional.

## Scenario Pitches

- [S1](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S1.md)
- [S2](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S2.md)
- [S3](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S3.md)
- [S4](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S4.md)
- [S5](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S5.md)
- [S6](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S6.md)
- [S7](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S7.md)
- [S8](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S8.md)
- [S9](/Users/niranjanj/Desktop/ucla/awd-arena-english/docs/patch-pitches/S9.md)
