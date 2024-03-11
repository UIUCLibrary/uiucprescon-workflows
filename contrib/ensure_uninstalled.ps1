param (
    [Parameter(Mandatory=$false)][string] $StartMenuShortCutRemoved,
    [Parameter(Mandatory=$false)][string] $TestInChocolateyList
)

$IsValid = $true

[int]$NumberOfTestsPerformed=0

if ($TestInChocolateyList){
    Write-Verbose "Package not show package in Chocolatey installed list"
    $Results = choco list --exact $TestInChocolateyList --limitoutput
    if($Results){
        Write-Host "Package not show package in Chocolatey installed list - Failed"
        $IsValid = $false
    } else {
        Write-Verbose "Package not show package in Chocolatey installed list - PASS"
    }
    $NumberOfTestsPerformed++
}

if ($StartMenuShortCutRemoved){
    Write-Verbose 'Windows start menu shortcut removed'
    if ([System.IO.File]::Exists($(Join-Path -Path "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs" -ChildPath $StartMenuShortCutRemoved))){
        Write-Host 'Windows start menu shortcut removed - Failed'
        $IsValid = $false
    } else {
        Write-Verbose 'Windows start menu shortcut removed - Success'
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
