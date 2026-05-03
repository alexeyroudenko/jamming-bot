#Requires -RunAsAdministrator
<#
.SYNOPSIS
    Compacts Docker Desktop WSL2 virtual disks (ext4.vhdx, docker_data.vhdx).

.DESCRIPTION
    1. Quit Docker Desktop (tray icon).
    2. Run this script in an elevated PowerShell (Run as administrator).
    3. Optional: free space inside Docker first: docker system prune -af
       (removes unused images/containers; use with care.)

.NOTES
    Windows Home: diskpart path is used if Optimize-VHD is unavailable.
#>
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'

function Test-Administrator {
    $id = [Security.Principal.WindowsIdentity]::GetCurrent()
    $p = [Security.Principal.WindowsPrincipal]::new($id)
    return $p.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

if (-not (Test-Administrator)) {
    Write-Error 'Run PowerShell as Administrator (right-click, Run as administrator).'
    exit 1
}

Write-Host 'Quit Docker Desktop, then press Enter...' -ForegroundColor Yellow
$null = Read-Host

Write-Host 'Shutting down WSL...' -ForegroundColor Cyan
& wsl.exe --shutdown
Start-Sleep -Seconds 3

$dockerWslRoot = Join-Path $env:LOCALAPPDATA 'Docker\wsl'
if (-not (Test-Path -LiteralPath $dockerWslRoot)) {
    Write-Error "Directory not found: $dockerWslRoot"
    exit 1
}

$vhdxFiles = Get-ChildItem -LiteralPath $dockerWslRoot -Recurse -Filter '*.vhdx' -File -ErrorAction SilentlyContinue |
    Sort-Object Length -Descending

if (-not $vhdxFiles) {
    Write-Error "No *.vhdx under $dockerWslRoot"
    exit 1
}

Write-Host 'VHDX files:' -ForegroundColor Cyan
$vhdxFiles | ForEach-Object { Write-Host ('  {0} ({1:N0} MB)' -f $_.FullName, ($_.Length / 1MB)) }

$useOptimizeVhd = $false
try {
    $null = Get-Command Optimize-VHD -ErrorAction Stop
    $useOptimizeVhd = $true
} catch {
    $useOptimizeVhd = $false
}

foreach ($f in $vhdxFiles) {
    $path = $f.FullName
    Write-Host "`nCompacting: $path" -ForegroundColor Green

    $compacted = $false
    if ($useOptimizeVhd) {
        try {
            Optimize-VHD -Path $path -Mode Full
            Write-Host 'Optimize-VHD: done.' -ForegroundColor Green
            $compacted = $true
        } catch {
            Write-Warning ("Optimize-VHD failed: {0}. Falling back to diskpart..." -f $_.Exception.Message)
            $useOptimizeVhd = $false
        }
    }

    if (-not $compacted) {
        $escaped = $path.Replace('"', '`"')
        $diskpartScript = @"
select vdisk file="$escaped"
attach vdisk readonly
compact vdisk
detach vdisk
"@
        $diskpartScript | & diskpart.exe
        if ($LASTEXITCODE -ne 0) {
            Write-Error "diskpart exited with code $LASTEXITCODE for: $path"
        }
        Write-Host 'diskpart: done.' -ForegroundColor Green
    }
}

Write-Host "`nDone. Start Docker Desktop again." -ForegroundColor Cyan
