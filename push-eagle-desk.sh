#!/usr/bin/env bash
# force-push this folder to GitHub (overwrites the remote cleanly)
set -e
REPO="https://github.com/nont-naraphat/eagle-desk.git"
[ -f main.py ] || { echo "run this from inside the eagle-desk folder"; exit 1; }
printf '.env\n__pycache__/\n*.pyc\n' > .gitignore
rm -rf .git
git init -q
git branch -M main
git config user.email "it@21sunpassion.com"
git config user.name  "nont"
git add -A
git commit -q -m "eagle-desk: multi-agent dashboard"
git remote add origin "$REPO"
git push -f origin main
echo "done -> $REPO (main)"
