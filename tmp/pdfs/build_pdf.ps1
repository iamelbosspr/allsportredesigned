$ErrorActionPreference = 'Stop'

New-Item -ItemType Directory -Force -Path 'output/pdf','tmp/pdfs' | Out-Null
$outFile = Join-Path (Get-Location) 'output/pdf/app-summary-one-page.pdf'

function Escape-PdfText([string]$s) {
    $s = $s -replace '\\','\\\\'
    $s = $s -replace '\(','\\('
    $s = $s -replace '\)','\\)'
    return $s
}

$ops = New-Object System.Collections.Generic.List[string]

function Add-Text([double]$x, [double]$y, [string]$font, [double]$size, [string]$text) {
    $esc = Escape-PdfText $text
    $script:ops.Add("BT /$font $size Tf $x $y Td ($esc) Tj ET")
}

$left = 54
$y = 752
Add-Text $left $y 'F2' 18 'App Summary (Repo Evidence)'
$y -= 28
Add-Text $left $y 'F2' 11 'What It Is'
$y -= 14
Add-Text $left $y 'F1' 9.5 'Not found in repo. This repository currently contains only .git metadata and no app files.'

$y -= 24
Add-Text $left $y 'F2' 11 "Who It's For"
$y -= 14
Add-Text $left $y 'F1' 9.5 'Primary user/persona: Not found in repo.'

$y -= 24
Add-Text $left $y 'F2' 11 'What It Does'
$y -= 14
$featureLines = @(
    '- No application features are implemented in the current repository state.',
    '- Git repository initialized (branch exists, no commits).',
    '- No source files found under workspace root.',
    '- No package/dependency manifests found.',
    '- No configuration files for runtime/services found.',
    '- No tests, scripts, or documentation found.'
)
foreach ($line in $featureLines) {
    Add-Text ($left + 14) $y 'F1' 9.5 $line
    $y -= 13
}

$y -= 10
Add-Text $left $y 'F2' 11 'How It Works (Architecture)'
$y -= 14
Add-Text $left $y 'F1' 9.5 'Components/services/data flow: Not found in repo.'
$y -= 13
Add-Text $left $y 'F1' 9.5 'Evidence basis: filesystem scan shows only .git internals; no runnable app artifacts.'

$y -= 24
Add-Text $left $y 'F2' 11 'How To Run'
$y -= 14
$runLines = @(
    '1. Not found in repo: no executable source, entrypoint, or run script detected.',
    '2. Not found in repo: no dependency manifest (e.g., package.json, pyproject.toml).',
    '3. Not found in repo: no setup instructions or README available.'
)
foreach ($line in $runLines) {
    Add-Text ($left + 14) $y 'F1' 9.5 $line
    $y -= 13
}
Add-Text 360 30 'F1' 8 'Generated from repository evidence only'

$streamContent = ($ops -join "`n") + "`n"
$len = [System.Text.Encoding]::ASCII.GetByteCount($streamContent)

$objects = @(
"1 0 obj`n<< /Type /Catalog /Pages 2 0 R >>`nendobj`n",
"2 0 obj`n<< /Type /Pages /Kids [3 0 R] /Count 1 >>`nendobj`n",
"3 0 obj`n<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R /F2 5 0 R >> >> /Contents 6 0 R >>`nendobj`n",
"4 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>`nendobj`n",
"5 0 obj`n<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>`nendobj`n",
"6 0 obj`n<< /Length $len >>`nstream`n$streamContent" + "endstream`nendobj`n"
)

$ms = New-Object System.IO.MemoryStream
$writer = New-Object System.IO.StreamWriter($ms, [System.Text.Encoding]::ASCII, 1024, $true)
$writer.NewLine = "`n"
$writer.Write("%PDF-1.4`n")
$writer.Flush()

$offsets = New-Object System.Collections.Generic.List[int]
foreach ($obj in $objects) {
    $offsets.Add([int]$ms.Position)
    $bytes = [System.Text.Encoding]::ASCII.GetBytes($obj)
    $ms.Write($bytes, 0, $bytes.Length)
}

$xrefPos = [int]$ms.Position
$writer.Write("xref`n0 7`n0000000000 65535 f `n")
foreach ($off in $offsets) {
    $writer.Write(($off.ToString('D10') + " 00000 n `n"))
}
$writer.Write("trailer`n<< /Size 7 /Root 1 0 R >>`nstartxref`n$xrefPos`n%%EOF`n")
$writer.Flush()

[System.IO.File]::WriteAllBytes($outFile, $ms.ToArray())
$writer.Dispose()
$ms.Dispose()

Get-Item $outFile | Select-Object FullName, Length, LastWriteTime
