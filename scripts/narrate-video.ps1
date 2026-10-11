$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$atmosVideoRoot = Join-Path (Get-Location) 'artifacts\video'
New-Item -ItemType Directory -Path $atmosVideoRoot -Force | Out-Null
$atmosScenes = Get-Content -Raw -LiteralPath 'scripts\video-storyboard.json' | ConvertFrom-Json
$atmosNarrator = New-Object System.Speech.Synthesis.SpeechSynthesizer
$atmosNarrator.SelectVoice('Microsoft Zira Desktop')
$atmosNarrator.Rate = 1
foreach ($atmosScene in $atmosScenes) {
    $atmosNarrator.SetOutputToWaveFile((Join-Path $atmosVideoRoot ($atmosScene.id + '.wav')))
    $atmosNarrator.Speak($atmosScene.narration)
    Write-Output ('Narrated ' + $atmosScene.id)
}
$atmosNarrator.Dispose()
