[CmdletBinding()]
param (
    [Parameter(Mandatory)]
    [string]$SpeedwagonExec
)
#param (
#    [Parameter(Mandatory=$false)][string] $StartMenuShortCut,
#    [Parameter(Mandatory=$false)][switch] $TestSpeedwagonVersion,
#    [Parameter(Mandatory=$false)][string] $TestInChocolateyList
#)

Write-Host 'Checking that application has properly installed'
[int]$NumberOfTestsPerformed=0
$IsValid = $true
function CheckInstalled( [string]$Name) {
    Write-Host "Checking Windows Management Win32 for <$APP_NAME>"
    $results = Get-WmiObject -Class Win32_Product -Filter "name = '$Name'"
    if (($results.Count) -ne 0)
    {
        Write-Host "Windows Management Win32 Product - Found"
        return $true
    }
    Write-Host "Windows Management Win32 Product - NOT FOUND"
    return $false

}
#if ($StartMenuShortCut){
#    Write-Verbose "Windows start menu Shortcut"
#    if (!([System.IO.File]::Exists($(Join-Path -Path "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs\\" -ChildPath $StartMenuShortCut)))){
#        Write-Host "Windows start menu Shortcut - Not Found"
#        $IsValid = $false
#    } else {
#        Write-Verbose "Windows start menu Shortcut - Found"
#    }
#    $NumberOfTestsPerformed++
#}
#
#if ($TestSpeedwagonVersion){
#    Write-Verbose "Speedwagon can display version text"
#    $SpeedwagonVersion = C:\ProgramData\chocolatey\lib\speedwagon_uiucprescon\tools\venv\Scripts\python.exe -m speedwagon --version
#    if($LASTEXITCODE -ne 0){
#        Write-Host "Speedwagon can display version text - Failed"
#        $IsValid = $false
#    } else {
#        Write-Verbose "Speedwagon version identified: $SpeedwagonVersion"
#        Write-Verbose "Speedwagon can display version text - PASS"
#    }
#    $NumberOfTestsPerformed++
#}
function Test-Info{
    [OutputType([bool])]
    param (
        [Parameter(Mandatory = $true)]
        [string]$SpeedwagonExec
    )
    $local:tempFile = [System.IO.Path]::GetTempFileName()
    $local:testSWInfo = Start-Process -FilePath $SpeedwagonExec -ArgumentList "info","--format=json" -NoNewWindow -PassThru -RedirectStandardOutput "$local:tempFile"
    $local:testSWInfo | Wait-Process -Timeout 20 -ErrorAction SilentlyContinue
    if (-not $local:testSWInfo.HasExited) {
        Write-Warning "Process exceeded timeout. Terminating..."
        $local:testSWInfo | Stop-Process -Force
        return $false
    }

    if ($local:testSWInfo.ExitCode -ne 0)
    {
        return $false
    }
    $local:jsonObject = Get-Content -Path $local:tempFile | ConvertFrom-Json
    foreach ($package in $jsonObject.installed_packages) {
        if( "$package" -like "speedwagon-contrib*"){
            return $true
        }
    }
    Write-Host "Found only"
    foreach ($package in $jsonObject.installed_packages) {
        Write-Host "* $package"
    }
    return $false
}

Write-Host "Speedwagon info"
if (Test-Info -SpeedwagonExec $SpeedwagonExec){
    Write-Host "Speedwagon info - PASS"
} else {
    Write-Host "Speedwagon info - Failed"
   $IsValid = $false
}
$NumberOfTestsPerformed++
#
#if ($TestInChocolateyList){
#    Write-Verbose "Package shows package in Chocolatey installed list"
#    $Results = choco list --exact $TestInChocolateyList --limitoutput
#    if(!($Results)){
#        Write-Host "Package shows package in Chocolatey installed list - Failed"
#        $IsValid = $false
#    } else {
#        Write-Verbose "Package shows package in Chocolatey installed list - PASS"
#    }
#    $NumberOfTestsPerformed++
#}
$APP_NAME = 'Speedwagon (UIUC Prescon Edition)'

if(!$(CheckInstalled -Name $APP_NAME)){
    $IsValid = $false
}
$NumberOfTestsPerformed++

Write-Host "$NumberOfTestsPerformed tests performed."
if ($NumberOfTestsPerformed -gt 0){
    if ($IsValid)
    {
        Write-Host "Success!"
        exit 0
    } else {
        Write-Host "Failed!"
        exit 1
    }

}
