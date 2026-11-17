# Render the report in Word, record the page each heading lands on (docs/report/toc_pages.json,
# read by build_report.js for the contents page) and export a PDF next to the .docx.
#   powershell -File scripts/report_toc_pages.ps1 [-Docx <path>]
param([string]$Docx)
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
if (-not $Docx) { $Docx = Join-Path $root 'docs\report\Sagar_Setu_Project_Report.docx' }
$pdf = [IO.Path]::ChangeExtension($Docx, '.pdf')
$json = Join-Path $root 'docs\report\toc_pages.json'

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $null
try {
    $doc = $word.Documents.Open($Docx, $false, $true)
    $doc.Repaginate()
    $pages = [ordered]@{}
    $paras = $doc.Paragraphs
    for ($i = 1; $i -le $paras.Count; $i++) {
        $p = $paras.Item($i)
        $style = $p.Style.NameLocal
        if ($style -like 'Heading [123]*') {
            $text = $p.Range.Text.Trim()
            if (-not $pages.Contains($text)) { $pages[$text] = $p.Range.Information(3) }
        }
        [void][Runtime.InteropServices.Marshal]::ReleaseComObject($p)
    }
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($paras)
    $total = $doc.ComputeStatistics(2)
    $doc.ExportAsFixedFormat([string]$pdf, 17)
    ($pages | ConvertTo-Json) | Out-File -Encoding utf8 $json
    "pages: $total"
    $pages.GetEnumerator() | ForEach-Object { "{0,4}  {1}" -f $_.Value, $_.Key }
}
finally {
    # Close and release every COM object, or a hidden WINWORD.EXE stays behind holding the
    # .docx open (seen 2026-11-17).
    if ($doc) { $doc.Close([ref]0); [void][Runtime.InteropServices.Marshal]::ReleaseComObject($doc) }
    $word.Quit([ref]0)
    [void][Runtime.InteropServices.Marshal]::ReleaseComObject($word)
    $doc = $null; $word = $null
    [GC]::Collect(); [GC]::WaitForPendingFinalizers(); [GC]::Collect()
}
