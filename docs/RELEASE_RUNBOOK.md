# AutoPassport MVP Release Runbook

## Purpose

This runbook defines the minimum reproducible procedure for approving and publishing the first AutoPassport MVP release.

## Preconditions

- Work from the repository root.
- Copy `.env.example` to `.env` and replace documented defaults before production deployment.
- Keep real VINs, registration numbers, credentials, tokens and private keys outside the repository.
- Do not increase `VERSION` while the release report contains failed steps.

## Release verification

Run the complete gate:

```bash
python scripts/release_check.py --report-path data/reports/release-check.json
```

The release is eligible only when the report contains:

```json
{
  "passed": true,
  "failed_steps": []
}
```

The gate covers repository privacy, runtime configuration, migrations, Python compilation, the complete test suite, restore and retention CLIs, and Docker Compose configuration.

## Backup and restore check

Before publishing a release candidate:

1. Create a backup through the admin API.
2. Verify the archive checksum and manifest.
3. Restore into an empty temporary destination:

```bash
python scripts/restore_backup.py path/to/backup.zip path/to/restore-target
```

4. Start the restored application against the restored database and confirm `/ready` returns HTTP 200.

## Container validation

Validate the committed deployment definition without requiring a local secret `.env` file:

```bash
docker compose --env-file .env.example config -q
```

For an actual deployment, use a private `.env` with production values and never commit it.

## Release approval

After a green report:

1. Record the verified commit SHA.
2. Move the relevant changelog entries from `Unreleased` into the release section.
3. Update `VERSION`.
4. Re-run the release gate against the version commit.
5. Create the release snapshot and SHA-256 digest.
6. Tag the verified commit.

## Rollback

If deployment readiness or data integrity checks fail:

1. Stop the new instance.
2. Preserve its logs and release report.
3. Restore the last verified backup into a new empty destination.
4. Start the previous verified image or commit.
5. Confirm `/ready` and the owner login flow before reopening access.
