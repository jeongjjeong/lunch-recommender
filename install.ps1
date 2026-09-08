<#
.SYNOPSIS
    Installs the "오늘 뭐 먹지?" lunch recommender to your local machine and opens it.

.DESCRIPTION
    Downloads lunch_recommender.html from the jeongjjeong/lunch-recommender GitHub
    repository into a local folder and opens it in your default browser. No build
    tools or dependencies are required - it's a single self-contained HTML file.

.EXAMPLE
    irm https://raw.githubusercontent.com/jeongjjeong/lunch-recommender/main/install.ps1 | iex
#>

[CmdletBinding()]
param(
    [string]$InstallDir = (Join-Path $env:USERPROFILE "lunch-recommender"),
    [string]$Branch = "main"
)

$ErrorActionPreference = "Stop"

$repoRawUrl = "https://raw.githubusercontent.com/jeongjjeong/lunch-recommender/$Branch/lunch_recommender.html"
$targetFile = Join-Path $InstallDir "lunch_recommender.html"

Write-Host "Installing lunch recommender to $InstallDir ..." -ForegroundColor Cyan

if (-not (Test-Path -Path $InstallDir)) {
    New-Item -ItemType Directory -Path $InstallDir | Out-Null
}

try {
    Invoke-WebRequest -Uri $repoRawUrl -OutFile $targetFile -UseBasicParsing
}
catch {
    Write-Error "Failed to download lunch_recommender.html: $_"
    exit 1
}

Write-Host "Downloaded to $targetFile" -ForegroundColor Green
Write-Host "Opening in your default browser..." -ForegroundColor Cyan

Start-Process $targetFile

Write-Host "Done! Enjoy your lunch." -ForegroundColor Green
