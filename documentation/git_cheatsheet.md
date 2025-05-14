


# 🧠 Git + GitHub Solo Dev Cheatsheet

## 🔧 Basic Setup
```bash
git config --global user.name "Your Name"
git config --global user.email "you@example.com"
```

## 🌀 Branch Workflow
```bash
git checkout -b feature/my-feature     # Create and switch to new branch
git checkout main                      # Switch back to main
git merge feature/my-feature           # Merge a feature branch into main
```

## ✅ Daily Commit Cycle
```bash
git status                             # See changes
git add .                              # Stage all changes
git commit -m "Clear, meaningful message"
git push                               # Push to current branch
```

> 🔁 If on a new branch:
```bash
git push -u origin branch-name         # Set upstream and push
```

## 🔄 Keeping Up To Date
```bash
git pull origin branch-name            # Pull latest changes
```

## 🔒 Protecting Secrets
Never commit API keys directly. Use `.env` or `.streamlit/secrets.toml` and ensure they're excluded from Git.

## 📦 Syncing Branches with GitHub
```bash
git checkout -b my-new-branch
git add .
git commit -m "Sync all local changes"
git push -u origin my-new-branch
```

Create a pull request:  
👉 `https://github.com/<your-username>/<repo>/pull/new/my-new-branch`

## 🛠 Fixing Mistakes
```bash
git restore filename.py                # Undo local change
git reset HEAD~1                       # Undo last commit (keep changes)
git reset --hard HEAD~1                # Undo last commit (discard changes)
```

## 📄 Viewing History
```bash
git log --oneline                      # One-line summary of commits
git diff                               # See uncommitted changes
git diff --staged                      # See staged changes
```

## 🧼 Cleaning Up
```bash
git clean -n                           # Preview untracked files to delete
git clean -f                           # Delete untracked files
```