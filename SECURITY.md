# Security policy

## Supported versions

Security fixes are provided for the latest `1.x` release. Older builds should be
upgraded before reporting a reproducibility problem.

## Reporting a vulnerability

Please use the repository’s **Security → Report a vulnerability** flow so the
report is created as a private GitHub Security Advisory. Do not open a public
issue for a vulnerability that could expose user files, bypass verification,
execute document content, leak sensitive values, or overwrite originals.

Include:

- CleanDrop version and Windows version;
- affected format and minimal reproduction steps;
- expected and observed verification checks;
- whether an original or output file was modified unexpectedly;
- a synthetic test file with no real personal data, if one is needed.

Do not attach private documents, real PII, access tokens, or credentials.

The project will acknowledge a complete report as soon as maintainers can review
it, coordinate a fix privately, and publish credit if the reporter wants it.
No fixed response deadline is promised for this volunteer project.

## Security boundaries

CleanDrop protects the transformation it performs; it is not a sandbox, malware
scanner, antivirus, steganography detector, or operating-system security product.
The full boundary is documented in [docs/threat-model.md](docs/threat-model.md).

## Automated security checks

Dependency auditing, secret scanning, dependency review, and Bandit checks run
in CI. Bandit rules B404 and B603 are excluded deliberately because Tesseract
and ExifTool are required local subprocesses. Every such call uses a fixed
executable, a list of arguments, `shell=False`, a timeout, and a checked return
code. All other Bandit rules remain enabled.

## Release integrity

Official artifacts are attached only to versioned GitHub Releases. Verify the
SHA-256 value against `SHA256SUMS.txt`. Unsigned 1.0 artifacts may trigger
SmartScreen; a warning alone is not proof of malware, but users should never
bypass it without checking the source URL and digest.
