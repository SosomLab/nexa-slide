# PowerPoint COM 으로 PPTX 의 글 상자마다 실제 줄 수를 읽는다 (브라우저 줄바꿈과 대조하는 검증용).
#   pwsh -NoProfile -File studio/lines_pptx.ps1 -Pptx out/ch00.pptx   → JSON 한 줄: [{"slide":1,"name":"e03 text","lines":2,"text":"…"}, …]
param(
  [Parameter(Mandatory = $true)][string]$Pptx
)
$ErrorActionPreference = 'Stop'
$Pptx = (Resolve-Path $Pptx).Path
$app = New-Object -ComObject PowerPoint.Application
$pres = $null
$out = @()
try {
  $pres = $app.Presentations.Open($Pptx, -1, 0, 0)
  foreach ($s in $pres.Slides) {
    foreach ($sh in $s.Shapes) {
      if ($sh.HasTextFrame -eq -1 -and $sh.TextFrame.HasText -eq -1) {
        $tr = $sh.TextFrame.TextRange
        $out += [pscustomobject]@{ slide = $s.SlideIndex; name = $sh.Name; lines = $tr.Lines().Count; text = $tr.Text }
      }
    }
  }
}
finally {
  if ($pres) { $pres.Close() }
  if ($app.Presentations.Count -eq 0) { $app.Quit() }
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$out | ConvertTo-Json -Compress -Depth 3
