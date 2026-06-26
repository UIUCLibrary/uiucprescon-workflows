param (
    [Parameter(mandatory=$true)]
    [string]$Wheel,
    [string]$uvExec,
    [string]$BuildPath = $(Join-Path -Path $PWD -ChildPath "build")

)

$ErrorActionPreference = 'Stop'

$APP_NAME="Speedwagon (UIUC Prescon Edition)"
$BOOTSTRAP_SCRIPT="./contrib/speedwagon_bootstrap.py"
$PACKAGE_SCRIPT_URL="https://github.com/UIUCLibrary/speedwagon_scripts/archive/refs/tags/v0.1.4.tar.gz"

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
        [string]$BuildPath
    )
    Write-Host "Build-Standalone"
    $fullPath = Join-Path -Path $BuildPath -ChildPath "package"
    $env:Path += ";$WixPath"
    & "$Uv" export --format pylock.toml --extra gui --extra contrib --no-dev --no-emit-project --no-header --output-file "${fullPath}\pylock.toml" | Out-Null
    & "$Uv" tool run --python 3.14 --from package-speedwagon@${PACKAGE_SCRIPT_URL} package_speedwagon $Wheel -r "${fullPath}\pylock.toml" --app-name="$APP_NAME" --app-bootstrap-script="$BOOTSTRAP_SCRIPT" --hidden-import="speedwagon_contrib"  --build-path="$fullPath"
    if ($LASTEXITCODE -ne 0){
        Write-Host "Failed to build using package-speedwagon"
        exit 1
    }

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

    function Locate-WixOnSystem(){
        return Get-Package -Name "WiX" -ErrorAction SilentlyContinue
    }

    function Locate-WixInBuildPath(){
        [CmdletBinding()]
        param (
            [Parameter(mandatory=$true)]
            [string]$packagePath
        )
        return Get-Package -Destination "$packagePath" -Name "WiX" -ErrorAction SilentlyContinue
    }

    function Install-Wix(){
        [CmdletBinding()]
        param (
            [Parameter(mandatory=$true)]
            [string]$packagePath
        )

        Install-Package -Name wix -Source $tempNugetSource -Force -ExcludeVersion -RequiredVersion 3.11.2 -Destination $packagePath | Out-Host -Paging
        return Get-Package -Destination $packagePath -Name "WiX"
    }

    $local:packageProviderName = "NuGet"

    if (-not (Get-PackageProvider -Name $local:packageProviderName -ErrorAction SilentlyContinue)) {
        Install-PackageProvider -Name $local:packageProviderName -MinimumVersion 2.8.5.208 -Force | Out-Host -Paging
    }

    $local:tempNugetSource = "MyNuGet"
    if (-not (Get-PackageSource -Name $local:tempNugetSource -ErrorAction SilentlyContinue)) {
        Register-PackageSource -Name $local:tempNugetSource -Location https://www.nuget.org/api/v2 -ProviderName $local:packageProviderName | Out-Host -Paging
    }

    $local:strategies = @(
        { Locate-WixInBuildPath -packagePath $path }
        { Locate-WixOnSystem }
        { Install-Wix -packagePath $path }
    )

    foreach ($strategy in $local:strategies) {
        $local:package = & $strategy
        if ($local:package){
            $local:toolsPath = Join-Path -Path $(Split-Path -Path $local:package.Source) -ChildPath "tools"
            if (Test-Path -Path (Join-Path -Path $local:toolsPath -ChildPath "wix.dll"))  {
                return $local:toolsPath
            }
        }
    }
}

$buildpath = Join-Path -Path $BuildPath -ChildPath "speedwagon_build"
if (-not (Test-Path -Path $buildpath -PathType Container)) {
    New-Item -ItemType Directory -Path $buildpath | Out-Null
}

Write-Host "Locating WiX Toolset"
$wixPath = Get-Wix -path $buildpath
if ($wixPath) {
    Write-Host "Locating WiX Toolset - Found"
} else {
    Write-Error "Locating WiX Toolset - Failed"
    exit 1
}
if ($uvExec -eq $null){
    $uvExec = Get-UV $buildpath
}
Build-Standalone -Uv "$uvExec" -Wheel "$Wheel" -WixPath "$wixPath" -BuildPath "$buildpath"
