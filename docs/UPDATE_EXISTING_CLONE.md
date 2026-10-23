# Updating an existing clone

This project update was prepared against base commit:

`bfc6343a786cf095282227636f1f93f7f9672ef8`

The included binary Git patch updates the existing repository without replacing its `.git` directory.

## Before applying

1. Save any local work and inspect `git status --short`.
2. Check `git rev-parse HEAD`. Apply this patch only if the current base is the commit above, or inspect/rebase the diff manually if the branch has moved.
3. Keep a backup of any locally edited files.

## Apply on Windows PowerShell

```powershell
git status --short
git rev-parse HEAD
git apply --check C:\path\to\gemma4-developer-agent-update-2026-10-23.patch
git apply --binary C:\path\to\gemma4-developer-agent-update-2026-10-23.patch
python -m pip install -r requirements-dev.txt
python tools/validate_submission.py
python tools/check_repo.py
python -m unittest discover -s tests -v
git diff --check
git status --short
```

Review the changes before committing:

```powershell
git add -A
git commit -m "Add budget-fit candidate and research evidence"
git push origin main
```

The patch does not push anything by itself. If `HEAD` differs from the expected base, use the complete clean-source archive as a reference rather than force-applying the patch.

## Important

`submission/` is the human-readable canonical source. The competition ZIP is built into the ignored `dist/submission.zip` directory. Local static checks do not replace the official Kaggle wheelhouse compiler or real Gemma smoke test.
