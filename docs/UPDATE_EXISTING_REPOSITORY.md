# Updating the Existing GitHub Repository

This project archive is a source-tree update and intentionally does not contain `.git`. Keep the `.git` directory of the existing local clone so its remote and commit history are preserved.

## Recommended safe workflow (Windows PowerShell)

1. Back up or commit any local work in the existing clone.
2. Extract the update archive to a temporary folder, for example `C:\temp\gemma4-developer-agent-update`.
3. Set `$Source` to that extracted folder and `$Repo` to the existing local clone. Verify that `$Repo\.git` exists before syncing.
4. Preview the changed file list and make sure the destination is the existing repository root. Because this is a full source tree, mirroring can remove obsolete files; do not point it at a parent directory.
5. Copy the source tree while explicitly excluding `.git`:

```powershell
$Source = "C:\temp\gemma4-developer-agent-update"
$Repo = "C:\path\to\existing\gemma4-developer-agent"
if (-not (Test-Path (Join-Path $Repo ".git"))) { throw "Destination is not an existing Git clone" }
if (-not (Test-Path (Join-Path $Source "README.md"))) { throw "Source repository root not found" }
robocopy $Source $Repo /MIR /XD .git /R:2 /W:1
if ($LASTEXITCODE -ge 8) { throw "Robocopy failed with exit code $LASTEXITCODE" }
```

6. Review the changes before committing:

```powershell
Set-Location $Repo
git status --short
python -m pip install -r requirements-dev.txt
python tools/validate_submission.py submission
python -m unittest discover -s tests -v
python tools/check_repo.py
```

7. If the checks and file review pass, commit and push to the existing `origin` remote:

```powershell
git add -A
git commit -m "Document latest Kaggle exception and organize research"
git push origin main
```

Do not run `git init` or add another remote when updating the existing repository. Do not run `git push --force`. If you have local work not represented in the archive, stop before syncing and merge it first.
