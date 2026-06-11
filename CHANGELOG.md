# Changelog

All notable changes to **PDF Flatten & Decrypt** are documented here.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.9] - 2026-06-11

### Added
- Startup disclaimer shown on **every launch**: an "as is", use-at-your-own-risk
  liability notice. **OK** continues to the app; **Cancel** closes it before the
  main window appears. (Shown each launch by design — the app stays stateless and
  writes no acceptance marker.)
- `LICENSE` (MIT, Copyright © 2026 Ahmedur Rahman) — free to use, modify, and
  distribute, provided the copyright and license notice are kept (attribution).

## [0.1.8] - 2026-06-10

### Changed
- Clearer handling of non-PDF input. Valid PDFs in a mixed selection are still
  processed; wrong-type files (e.g. `.txt`) are listed under "Skipped (not a PDF)";
  dropping only non-PDF files names them instead of showing a generic message.

### Fixed
- A file with a `.pdf` name that isn't a valid PDF is now reported **once** as a
  failure with a plain-language reason, instead of a duplicated, technical error.

## [0.1.7] - 2026-06-10

### Added
- Responsive processing for large documents: rendering runs on a background
  thread, so the window stays responsive even on long PDFs (200+ pages).
- Per-page progress bar with a **Cancel** button; cancelling leaves no partial
  output on the Desktop.
- Advisory confirmation for documents of 50+ pages (processing may take a while,
  and the fax plan must support sending that many pages). Informational only —
  it never blocks processing and imposes no page limit.

### Fixed
- Fixed a blank progress window ("Working…" with no contents) caused by an invalid
  widget padding value. This supersedes the withdrawn 0.1.6 build, which contained
  that bug.

### Changed
- CI build actions bumped to Node 24 majors ahead of GitHub's forced migration.

## [0.1.5] - 2026-06-10

### Security
- Hardening pass: a per-page render **pixel cap** so a hostile page size can't
  force a huge memory allocation; **exclusive output writes** so a planted symlink
  at a predictable output name can't redirect the write; and **pinned dependencies**.

### Changed
- CI retries release-asset uploads to survive GitHub's intermittent 401 errors.

## [0.1.4] - 2026-06-10

### Added
- Dropped files now prompt for an action: **Flatten to PDF** or **Convert to JPG**.

## [0.1.3] - 2026-06-10

### Added
- PDF → JPG fallback mode: save one image per page into a folder on the Desktop.

## [0.1.2] - 2026-06-10

### Changed
- Flattening now produces **bitonal CCITT Group 4** output — far smaller,
  fax-native files.
- Releases are published via the GitHub CLI (more robust than the prior
  third-party action).

## [0.1.1] - 2026-06-10

### Added
- About dialog with developer credit.

## [0.1.0] - 2026-06-10

### Added
- Initial release: an offline desktop app that decrypts and flattens PDF files,
  with a test suite and CI that produces a portable Windows build.

[0.1.9]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.8...v0.1.9
[0.1.8]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.7...v0.1.8
[0.1.7]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.5...v0.1.7
[0.1.5]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.4...v0.1.5
[0.1.4]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.3...v0.1.4
[0.1.3]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.2...v0.1.3
[0.1.2]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.1...v0.1.2
[0.1.1]: https://github.com/asrahmann/PDF-Flattner/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/asrahmann/PDF-Flattner/releases/tag/v0.1.0
