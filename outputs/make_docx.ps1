$txtFile = "C:\Users\GamePC\Desktop\AI Anti-anti plag\outputs\literature_review_salmon.txt"
$docxFile = "C:\Users\GamePC\Desktop\AI Anti-anti plag\outputs\literature_review_salmon.docx"

$lines = Get-Content -Path $txtFile -Encoding UTF8

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$doc = $word.Documents.Add()
$sel = $word.Selection

# GOST 7.32-2017 page setup
$ps = $doc.Sections(1).PageSetup
$ps.LeftMargin   = $word.CentimetersToPoints(3.0)
$ps.RightMargin  = $word.CentimetersToPoints(1.5)
$ps.TopMargin    = $word.CentimetersToPoints(2.0)
$ps.BottomMargin = $word.CentimetersToPoints(2.0)

$wdAlignLeft    = 0
$wdAlignCenter  = 1
$wdAlignJustify = 3
$wdLineSpace1pt5 = 1   # wdLineSpace1pt5
$wdStory        = 6   # wdStory (end of document)
$wdFormatDocx   = 16  # wdFormatDocumentDefault

function Set-Fmt {
    param([int]$align=3, [bool]$bold=$false, [bool]$fi=$true, [int]$size=14)
    $sel.Font.Name  = "Times New Roman"
    $sel.Font.Size  = $size
    $sel.Font.Bold  = $bold
    $sel.ParagraphFormat.Alignment       = $align
    $sel.ParagraphFormat.LineSpacingRule = $wdLineSpace1pt5
    $sel.ParagraphFormat.SpaceBefore     = 0
    $sel.ParagraphFormat.SpaceAfter      = 0
    if ($fi) {
        $sel.ParagraphFormat.FirstLineIndent = $word.CentimetersToPoints(1.25)
        $sel.ParagraphFormat.LeftIndent      = 0
    } else {
        $sel.ParagraphFormat.FirstLineIndent = 0
        $sel.ParagraphFormat.LeftIndent      = 0
    }
}

function Write-Line {
    param([string]$text, [int]$align=3, [bool]$bold=$false, [bool]$fi=$true, [int]$size=14)
    if ([string]::IsNullOrWhiteSpace($text)) { return }
    Set-Fmt -align $align -bold $bold -fi $fi -size $size
    $sel.TypeText($text)
    $sel.TypeParagraph()
    $sel.Font.Bold = $false
}

function Add-MdTable {
    param([string[]]$tLines)
    # Skip separator rows (|---| lines)
    $dataRows = @()
    foreach ($row in $tLines) {
        $stripped = $row -replace '\|', '' -replace '-', '' -replace ':', '' -replace '\s', ''
        if ($stripped.Length -eq 0) { continue }
        $dataRows += $row
    }
    if ($dataRows.Count -eq 0) { return }

    $parsedRows = @()
    foreach ($row in $dataRows) {
        $parts = $row -split '\|'
        $cells = @()
        foreach ($p in $parts) {
            $t = $p.Trim()
            if ($t.Length -gt 0) { $cells += $t }
        }
        if ($cells.Count -gt 0) { $parsedRows += ,@($cells) }
    }
    if ($parsedRows.Count -eq 0) { return }

    $numRows = $parsedRows.Count
    $numCols = 1
    foreach ($r in $parsedRows) { if ($r.Count -gt $numCols) { $numCols = $r.Count } }

    $range = $sel.Range
    $tbl = $doc.Tables.Add($range, $numRows, $numCols)
    try { $tbl.Style = "Table Grid" } catch { }
    $tbl.AllowAutoFit = $true

    for ($r = 0; $r -lt $parsedRows.Count; $r++) {
        $rd = $parsedRows[$r]
        for ($c = 0; $c -lt $rd.Count -and $c -lt $numCols; $c++) {
            $cell = $tbl.Cell($r + 1, $c + 1)
            $cell.Range.Font.Name = "Times New Roman"
            $cell.Range.Font.Size = 11
            $cell.Range.Font.Bold = ($r -eq 0)
            $cell.Range.ParagraphFormat.Alignment = $wdAlignLeft
            $txt = $rd[$c]
            # Remove trailing paragraph mark artifact before setting text
            $cell.Range.Text = $txt
        }
    }

    # Move past table
    $sel.EndKey($wdStory)
    $sel.TypeParagraph()
}

# ---- Find title block end (first ===... line) ----
$firstSep = -1
for ($i = 0; $i -lt $lines.Count; $i++) {
    if ($lines[$i] -match '^={10,}') { $firstSep = $i; break }
}

# ---- Title block ----
for ($i = 0; $i -lt $firstSep; $i++) {
    $ln = $lines[$i]
    if ([string]::IsNullOrWhiteSpace($ln)) { continue }
    if ($i -eq 0) {
        # Main title: "LITERATURE REVIEW"
        Write-Line -text $ln -align $wdAlignCenter -bold $true -fi $false -size 16
    } elseif ($i -le 4) {
        Write-Line -text $ln -align $wdAlignCenter -bold $true -fi $false -size 14
    } else {
        Write-Line -text $ln -align $wdAlignCenter -bold $false -fi $false -size 14
    }
}
# Blank spacer after title
$sel.TypeParagraph()

# ---- Body state machine ----
$inTable   = $false
$tableBuf  = @()
$paraBuf   = @()
$inRefs    = $false

function Flush-Para {
    if ($script:paraBuf.Count -eq 0) { return }
    $txt = ($script:paraBuf -join " ").Trim()
    $script:paraBuf = @()
    if ([string]::IsNullOrWhiteSpace($txt)) { return }
    if ($script:inRefs) {
        Write-Line -text $txt -align $wdAlignLeft -bold $false -fi $false -size 14
    } else {
        Write-Line -text $txt -align $wdAlignJustify -bold $false -fi $true -size 14
    }
}

for ($i = ($firstSep + 1); $i -lt $lines.Count; $i++) {
    $ln = $lines[$i]

    # Skip separators and end marker
    if ($ln -match '^={10,}' -or $ln -match '^END OF DOCUMENT') {
        Flush-Para
        continue
    }

    # Table row detection
    if ($ln -match '^\|') {
        if (-not $inTable) { Flush-Para; $inTable = $true; $tableBuf = @() }
        $tableBuf += $ln
        continue
    } else {
        if ($inTable) {
            Add-MdTable -tLines $tableBuf
            $inTable = $false
            $tableBuf = @()
        }
    }

    # Blank line = paragraph break
    if ([string]::IsNullOrWhiteSpace($ln)) {
        Flush-Para
        continue
    }

    # Section headings
    if ($ln -match '^(INTRODUCTION|SECTION \d+:|REFERENCES)') {
        Flush-Para
        if ($ln -match '^REFERENCES') { $inRefs = $true }
        Write-Line -text $ln -align $wdAlignLeft -bold $true -fi $false -size 14
        continue
    }

    # Table caption (Table N — ...)
    if ($ln -match '^Table \d+') {
        Flush-Para
        Write-Line -text $ln -align $wdAlignLeft -bold $false -fi $false -size 14
        continue
    }

    # Accumulate text
    $paraBuf += $ln
}

Flush-Para

# ---- Save ----
if (Test-Path $docxFile) { Remove-Item $docxFile -Force }
$doc.SaveAs2($docxFile, $wdFormatDocx)
$doc.Close($false)
$word.Quit()

Write-Host "Saved: $docxFile"
