param (
    [Parameter(mandatory=$true)]
    [string]$Wheel,
    [Parameter(mandatory=$true)]
    [string]$ExtraIndexUrl,
    [string]$uvExec
)

$APP_NAME="Speedwagon (UIUC Prescon Edition)"
$BOOTSTRAP_SCRIPT="./contrib/speedwagon_bootstrap.py"
$PACKAGE_SCRIPT_URL="https://github.com/UIUCLibrary/speedwagon_scripts/archive/refs/tags/v0.1.0.tar.gz"


function Build-Standalone{
    [CmdletBinding()]
    param (
        [Parameter(mandatory=$true)]
        [string]$Uv,
        [Parameter(mandatory=$true)]
        [string]$Wheel,
        [Parameter(mandatory=$true)]
        [string]$WixPath,
        [Parameter(mandatory=$true)]
        [string]$ExtraIndexUrl
    )
    Write-Host "Build-Standalone"
    $tempPath = [System.IO.Path]::GetTempPath()
    $dirName = (New-Guid).ToString("N")
    $fullPath = Join-Path -Path $tempPath -ChildPath $dirName
    New-Item -ItemType Directory -Path $fullPath | Out-Null
    $env:Path += ";$WixPath"
    $env:PIP_EXTRA_INDEX_URL = "$ExtraIndexUrl"
    $env:UV_EXTRA_INDEX_URL = "$ExtraIndexUrl"
    & "$Uv" export --no-hashes --format requirements-txt --extra gui --no-dev --no-emit-project > "${fullPath}\requirements-gui.txt"
    & "$Uv" tool run --with-requirements "${fullPath}\requirements-gui.txt" --python 3.11 --from package_speedwagon@${PACKAGE_SCRIPT_URL} package_speedwagon $Wheel -r "${fullPath}\requirements-gui.txt" --app-name="$APP_NAME" --app-bootstrap-script="$BOOTSTRAP_SCRIPT"

}
function Get-UV() {
    [CmdletBinding()]
    param (
        [Parameter(mandatory=$true)]
        [string]$buildPath
    )
    py -m venv $buildpath\venv
    & "$buildPath\venv\Scripts\pip.exe" --disable-pip-version-check install uv | Out-Null
    return Join-Path "$buildPath" -ChildPath "venv\Scripts\uv.exe"

}

function Get-Wix{
    [CmdletBinding()]
    param (
        [Parameter(mandatory=$true)]
        [string]$path
    )
    Install-PackageProvider -Name NuGet -MinimumVersion 2.8.5.208 -Force | Out-Host -Paging
    Register-PackageSource -Name MyNuGet -Location https://www.nuget.org/api/v2 -ProviderName NuGet | Out-Host -Paging
    Install-Package -Name wix -Source MyNuGet -Force -ExcludeVersion -RequiredVersion 3.11.2 -Destination $path | Out-Host -Paging
    return Join-Path -Path $path -ChildPath "WiX\tools"
}
$tempPath = [System.IO.Path]::GetTempPath()
$dirName = (New-Guid).ToString("N")
$buildpath = Join-Path -Path $tempPath -ChildPath $dirName
New-Item -ItemType Directory -Path $buildpath | Out-Null

$wixPath = Get-Wix -path $buildpath
if ($uvExec -eq $null){
    $uvExec = Get-UV $buildpath
}
Build-Standalone -Uv "$uvExec" -Wheel "$Wheel" -WixPath "$wixPath" -ExtraIndexUrl "$ExtraIndexUrl"
