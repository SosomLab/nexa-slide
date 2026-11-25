# Word COM 으로 DOCX 를 PDF 로 바꾼다(페이지 문서 내보내기 - export_docx.py 가 만든 파일). Windows + Word 가 있을 때만.
#   pwsh -NoProfile -File studio/render_docx.ps1 -Docx out/report.docx -Pdf out/report.pdf
# 우리가 띄운 Word 만 쓰고 끝낸다(사용자가 열어 둔 Word 창·문서는 건드리지 않는다). 원본은 읽기 전용으로 열고 저장하지 않는다.
# 매크로는 강제로 끄고(AutomationSecurity 3) 경고 창을 띄우지 않는다. 이 파일은 BOM 이 있어야 pwsh 가 한글 주석을 바르게 읽는다.
param([Parameter(Mandatory = $true)][string]$Docx, [Parameter(Mandatory = $true)][string]$Pdf)
$ErrorActionPreference = "Stop"
$Docx = (Resolve-Path $Docx).Path
$pdfPath = [System.IO.Path]::GetFullPath($Pdf)
if (Test-Path $pdfPath) { Remove-Item $pdfPath -Force }
$word = New-Object -ComObject Word.Application
$doc = $null
try {
  $word.Visible = $false; $word.DisplayAlerts = 0; $word.AutomationSecurity = 3
  # Open(FileName, ConfirmConversions, ReadOnly, AddToRecentFiles)
  $doc = $word.Documents.Open($Docx, $false, $true, $false)
  # ExportAsFixedFormat(OutputFileName, ExportFormat 17 = PDF, OpenAfterExport, OptimizeFor 0 = 인쇄, Range 0 = 전체, From, To, Item 0 = 본문, IncludeDocProps, KeepIRM, CreateBookmarks 1 = 제목)
  $doc.ExportAsFixedFormat($pdfPath, 17, $false, 0, 0, 0, 0, 0, $true, $true, 1)
  $pages = $doc.ComputeStatistics(2)  # wdStatisticPages
  Write-Output "pdf $pdfPath"
  Write-Output "pages $pages"
}
finally {
  if ($doc) { $doc.Close(0) }   # wdDoNotSaveChanges
  $word.Quit(0)
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($word) | Out-Null
}
