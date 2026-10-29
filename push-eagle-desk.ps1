# force-push this folder to GitHub (overwrites the remote cleanly)
# run from inside the eagle-desk folder:  .\push-eagle-desk.ps1
$repo = 'https://github.com/nont-naraphat/eagle-desk.git'
if (-not (Test-Path main.py)) { Write-Host 'run this from inside the eagle-desk folder'; exit 1 }
".env`n__pycache__/`n*.pyc" | Set-Content -Encoding ASCII .gitignore
if (Test-Path .git) { Remove-Item -Recurse -Force .git }
git init
git branch -M main
git config user.email "it@21sunpassion.com"
git config user.name  "nont"
git add -A
git commit -m "eagle-desk: multi-agent dashboard"
git remote add origin $repo
git push -f origin main
Write-Host "done -> $repo (main)"
