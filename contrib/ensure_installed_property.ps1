param (
    [Parameter(Mandatory=$false)][string] $StartMenuShortCut,
    [Parameter(Mandatory=$false)][switch] $TestSpeedwagonVersion,
    [Parameter(Mandatory=$false)][string] $TestInChocolateyList
)
[int]$NumberOfTestsPerformed=0

$IsValid = $true
if ($StartMenuShortCut){
    Write-Verbose "Windows start menu Shortcut"
    if (!([System.IO.File]::Exists($(Join-Path -Path "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs" -ChildPath $StartMenuShortCut)))){
        Write-Host "Windows start menu Shortcut - Not Found"
        $IsValid = $false
    } else {
        Write-Verbose "Windows start menu Shortcut - Found"
    }
    $NumberOfTestsPerformed++
}

if ($TestSpeedwagonVersion){
    Write-Verbose "Speedwagon can display version text"
    $SpeedwagonVersion = C:\ProgramData\chocolatey\lib\speedwagon_uiucprescon\tools\venv\Scripts\python.exe -m speedwagon --version
    if($LASTEXITCODE -ne 0){
        Write-Host "Speedwagon can display version text - Failed"
        $IsValid = $false
    } else {
        Write-Verbose "Speedwagon version identified: $SpeedwagonVersion"
        Write-Verbose "Speedwagon can display version text - PASS"
    }
    $NumberOfTestsPerformed++
}

if ($TestInChocolateyList){
    Write-Verbose "Package shows package in Chocolatey installed list"
    $Results = choco list --exact $TestInChocolateyList --limitoutput
    if(!($Results)){
        Write-Host "Package shows package in Chocolatey installed list - Failed"
        $IsValid = $false
    } else {
        Write-Verbose "Package shows package in Chocolatey installed list - PASS"
    }
    $NumberOfTestsPerformed++
}


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
