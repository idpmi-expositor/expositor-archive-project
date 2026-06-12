# Google Drive sync setup

This repository has two Google Drive touchpoints:

- `.github/workflows/sync-drive.yml` can sync the shared Drive folder
  `ExpositorMain` into the repository path `ExpositorMain/`.
- `scripts/ingestion/00_validate_source_pdf_sync.py` validates that local
  source PDFs in `source_assets/original_pdfs` match a Drive source folder by
  filename and size.

The root pipeline paths are canonical for local processing. `ExpositorMain/`
is synced evidence from Drive; `ExpositorMain/outputs` is legacy/generated and
must not be treated as canonical archive data.

Drive folder ID:

```text
18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n
```

## Local source PDF validation folder

The source-PDF pipeline can also validate `source_assets/original_pdfs` against
a Drive folder through local `rclone`. This is separate from the full
`ExpositorMain` GitHub Actions sync above.

Current source PDF folder ID:

```text
1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

Validate local PDF filenames and sizes with:

```bash
python scripts/ingestion/00_validate_source_pdf_sync.py --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

If the rclone config is not installed in the default user location, pass it
explicitly:

```bash
python scripts/ingestion/00_validate_source_pdf_sync.py --rclone-config path/to/rclone.conf --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

If the validator reports a mismatch, sync the missing PDF files locally, run
the rename utility, and validate again before generating downstream artifacts:

```bash
python scripts/ingestion/00_rename_source_pdfs.py
python scripts/ingestion/00_rename_source_pdfs.py --apply
python scripts/ingestion/00_validate_source_pdf_sync.py --drive-root-folder-id 1LX-wYECeqZVD_Uwe8ZEpfFL9oicVdeG7
```

## Security rule

Do not put the Google account username or password in GitHub, workflow YAML, issue comments, commit messages, or logs. Use the password only to sign in during the local rclone authorization flow.

## Create the rclone config

On a trusted local machine:

1. Install rclone: https://rclone.org/downloads/
2. Run:

```bash
rclone config
```

3. Create a new remote named exactly:

```text
gdrive
```

4. Choose Google Drive as the storage provider.
5. Use the default OAuth flow unless you have a dedicated Google Cloud OAuth client.
6. Sign in as an account that can read the `ExpositorMain` folder and the
   source PDF validation folder when the browser opens.
7. Choose a Drive scope that can read file contents, such as full Drive access or read-only Drive access.
8. Confirm the remote can see the folder by using the folder ID as the remote root:

```bash
rclone lsd 'gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:'
rclone ls 'gdrive,root_folder_id=18J7kB4mUpNU7J7aPn17xl7SQOSYYyO7n:' --max-depth 1
```

## Add the GitHub secret

In GitHub, open this repository, then go to:

```text
Settings -> Secrets and variables -> Actions -> New repository secret
```

Create a repository secret named:

```text
RCLONE_CONFIG
```

Set the value to the full contents of your local `rclone.conf` file.

Common locations:

```text
Windows: %APPDATA%\\rclone\\rclone.conf
macOS/Linux: ~/.config/rclone/rclone.conf
```

The config should include a section like:

```text
[gdrive]
type = drive
token = {...}
```

Do not commit real rclone tokens. The repository ignores the local `rclone/`
folder so operators can keep private config copies there when needed.

## First run

1. Open the repository's Actions tab.
2. Select `Sync Google Drive folder`.
3. Click `Run workflow`.
4. Leave `dry_run` as `true` for the first run.
5. Inspect the logs and confirm the listed changes are expected.
6. Run it again with `dry_run` set to `false` to commit the synced Drive files.

## Notes

- Google Docs, Sheets, and Slides are exported using `docx`, `xlsx`, `pptx`, and `pdf` formats.
- Binary files and regular uploaded files are copied as-is.
- The workflow commits changes to the repository using `github-actions[bot]`.
- The workflow is manual-only until a schedule is intentionally added.
