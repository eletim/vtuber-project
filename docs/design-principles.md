# Design principles recovery status

## Status

The authoritative design principles could not be recovered. This file records
that blocker only; it is not a replacement design-principles specification and
must not be used to infer or approve artwork decisions.

## Recovery evidence

As of 2026-10-19, `docs/design-principles.md` is absent from:

- the complete reachable Git history and all local and remote branches;
- GitHub's `dev/v0.3.0` tree, commit history for this path, and repository code
  search;
- all GitHub pull-request refs, issues, and issue comments; and
- the local repository's reflogs and unreachable Git objects.

The `dev/v0.3.0` baseline inspected for recovery is commit
`ae355f4c8b9bb3a7b91ca9ab907a02a43d3d52cf`. The only GitHub pull-request heads
available at inspection time were commits
`6aafc2835987b73680dddbee0d00aa71ca2ce246` (PR #1) and
`ae355f4c8b9bb3a7b91ca9ab907a02a43d3d52cf` (PR #2); neither contains the file.

## Precise blocker

No authoritative content, commit or blob identifier, retained branch, pull
request, issue attachment, or repository-local copy containing the missing
principles is available. Existing README, v7/v8 worklogs, scripts, and Issue #3
describe implementation history or individual artwork constraints, but none is
identified as the authoritative design-principles source. Converting those
materials into principles would therefore invent the missing baseline.

Recovery requires the original document or an immutable identifier for an
authoritative copy to be supplied by its owner. Until then, design decisions
that depend on these principles remain blocked.
