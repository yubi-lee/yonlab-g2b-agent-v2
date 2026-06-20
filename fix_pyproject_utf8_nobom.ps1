$ErrorActionPreference = "Stop"

$ProjectRoot = "D:\Views\yonlab-g2b-agent-v2"
Set-Location $ProjectRoot

$pyproject = @'
[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "-q"

[tool.ruff]
line-length = 100
target-version = "py311"

[tool.ruff.lint]
select = ["E", "F", "I", "UP", "B"]
ignore = []
'@

$utf8NoBom = New-Object System.Text.UTF8Encoding($false)
[System.IO.File]::WriteAllText((Join-Path $ProjectRoot "pyproject.toml"), $pyproject, $utf8NoBom)

Write-Host "[OK] Rewrote pyproject.toml as UTF-8 without BOM." -ForegroundColor Green

if (Test-Path ".\.venv\Scripts\Activate.ps1") {
    . .\.venv\Scripts\Activate.ps1
}

Write-Host "[INFO] Running pytest..." -ForegroundColor Cyan
python -m pytest -q
