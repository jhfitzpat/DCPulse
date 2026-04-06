# Manually push local repo state to the Debian VM (after editing prompts, data/, src/, etc.).
# Prerequisites: SSH key access to the VM; on the VM, repo cloned and setup-vm.sh already run.
#
# Environment (or pass parameters):
#   DC_PULSE_VM_HOST    - hostname or IP (required)
#   DC_PULSE_VM_PATH    - absolute path to repo on VM, e.g. /home/you/DCPulse (required)
#   DC_PULSE_SSH_USER   - optional SSH user (default: current Windows user name may not match; set explicitly)
#   DC_PULSE_DEPLOY_MODE - "git" (default) or "rsync"
#   DC_PULSE_GIT_BRANCH - branch to checkout on VM when using git mode (default: master)
#
# Git mode: commit and push to your remote first, then this script runs git pull on the VM.
# Rsync mode: requires rsync in PATH (e.g. WSL, Cygwin, or cwRsync); copies working tree without a push.

param(
    [string] $VmHost = $env:DC_PULSE_VM_HOST,
    [string] $RemotePath = $env:DC_PULSE_VM_PATH,
    [ValidateSet("git", "rsync")]
    [string] $Mode = $(if ($env:DC_PULSE_DEPLOY_MODE) { $env:DC_PULSE_DEPLOY_MODE } else { "git" }),
    [string] $Branch = $(if ($env:DC_PULSE_GIT_BRANCH) { $env:DC_PULSE_GIT_BRANCH } else { "master" }),
    [string] $SshUser = $env:DC_PULSE_SSH_USER
)

$ErrorActionPreference = "Stop"

if (-not $VmHost) {
    throw "Set DC_PULSE_VM_HOST or pass -VmHost"
}
if (-not $RemotePath) {
    throw "Set DC_PULSE_VM_PATH or pass -RemotePath"
}

$sshTarget = if ($SshUser) { "${SshUser}@${VmHost}" } else { $VmHost }

if ($Mode -eq "git") {
    Write-Host "Remote: git fetch / checkout $Branch / pull + pip install (push from your PC first)."
    $remoteCmd = "set -e; cd '$RemotePath'; git fetch origin; git checkout '$Branch'; git pull --ff-only; chmod +x scripts/*.sh; .venv/bin/pip install -q -r requirements.txt"
    ssh $sshTarget $remoteCmd
    Write-Host "Done."
    exit 0
}

if (-not (Get-Command rsync -ErrorAction SilentlyContinue)) {
    throw "rsync not found in PATH. Use -Mode git or install rsync (e.g. WSL), or run scripts/deploy-update.sh from Git Bash."
}

$repoRoot = (Resolve-Path (Join-Path $PSScriptRoot "..")).Path
Set-Location $repoRoot

$rsyncArgs = @(
    "-avz",
    "--exclude=.git/", "--exclude=.venv/", "--exclude=.env",
    "--exclude=__pycache__/", "--exclude=.cursor/", "--exclude=last_digest.txt",
    "--exclude=logs/", "--exclude=archive/", "--exclude=.pytest_cache/",
    "--exclude=.mypy_cache/", "--exclude=.ruff_cache/", "--exclude=*.egg-info/"
)

$dest = "${sshTarget}:${RemotePath}/"
Write-Host "rsync $repoRoot/ -> $dest"
& rsync @rsyncArgs ./ $dest
ssh $sshTarget "set -e; cd '$RemotePath'; chmod +x scripts/*.sh; .venv/bin/pip install -q -r requirements.txt"
Write-Host "Done."
