#param (
#    [Parameter(Mandatory=$false)][string] $StartMenuShortCutRemoved,
#    [Parameter(Mandatory=$false)][string] $TestInChocolateyList
#)
#
#Write-Host 'Checking that no remaining files are installed'
$IsValid = $true
#

[int]$NumberOfTestsPerformed=0

function CheckUninstalled( [string]$Name){
    Write-Host "Checking Application not installed"
    $results = Get-WmiObject -Class Win32_Product -Filter "name = '$Name'"
    if (($results.Count) -ne 0){
        Write-Host "Checking Application not installed - Failed"
        return $false
    } else {
        Write-Host "Checking Application not installed - Passed"
        return $true
    }
}


#
#if ($TestInChocolateyList){
#    Write-Verbose "Package not show package in Chocolatey installed list"
#    $Results = choco list --exact $TestInChocolateyList --limitoutput
#    if($Results){
#        Write-Host "Package not show package in Chocolatey installed list - Failed"
#        $IsValid = $false
#    } else {
#        Write-Verbose "Package not show package in Chocolatey installed list - PASS"
#    }
#    $NumberOfTestsPerformed++
#}
#
#if ($StartMenuShortCutRemoved){
#    Write-Verbose 'Windows start menu shortcut removed'
#    if ([System.IO.File]::Exists($(Join-Path -Path "$Env:ProgramData\\Microsoft\\Windows\\Start Menu\\Programs" -ChildPath $StartMenuShortCutRemoved))){
#        Write-Host 'Windows start menu shortcut removed - Failed'
#        $IsValid = $false
#    } else {
#        Write-Verbose 'Windows start menu shortcut removed - Success'
#    }
#    $NumberOfTestsPerformed++
#}

if(!$(CheckUninstalled 'Speedwagon UIUC Prescon')){
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
