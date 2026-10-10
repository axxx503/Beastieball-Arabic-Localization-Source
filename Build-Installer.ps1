param([Parameter(Mandatory=$true)][string]$Xdelta3Path, [string]$RuntimeDllPath)
$ErrorActionPreference='Stop'
$root=$PSScriptRoot
$payload=Join-Path $root 'installer-payload'
Copy-Item -LiteralPath $Xdelta3Path -Destination (Join-Path $payload 'xdelta3.exe') -Force

Add-Type -AssemblyName System.IO.Compression.FileSystem
$archive=Join-Path $root 'build-payload.zip'
if(Test-Path -LiteralPath $archive){Remove-Item -LiteralPath $archive}
[System.IO.Compression.ZipFile]::CreateFromDirectory($payload,$archive)
$compiler=Join-Path $env:WINDIR 'Microsoft.NET\Framework64\v4.0.30319\csc.exe'
$out=Join-Path $root 'Beastieball-Arabic-Localization-All-in-One.exe'
& $compiler /nologo /target:winexe /platform:x64 /reference:System.Windows.Forms.dll /reference:System.Drawing.dll /reference:System.Web.Extensions.dll /reference:System.IO.Compression.dll /reference:System.IO.Compression.FileSystem.dll ('/resource:'+$archive+',payload.zip') ('/out:'+$out) (Join-Path $root 'Installer.cs')
if($LASTEXITCODE -ne 0){throw 'Installer compilation failed'}
Write-Output $out
