# PowerPoint COM 으로 PPTX 슬라이드를 PNG 로 내보낸다 (실제 PowerPoint 렌더 미리보기).
#   pwsh -NoProfile -File studio/render_pptx.ps1 -Pptx out/ch00.pptx -OutDir out/ch00 [-Width 1280]
param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [Parameter(Mandatory = $true)][string]$OutDir,
  [int]$Width = 1280
)
$ErrorActionPreference = 'Stop'
$Pptx = (Resolve-Path $Pptx).Path
New-Item -ItemType Directory -Force $OutDir | Out-Null
$OutDir = (Resolve-Path $OutDir).Path
Get-ChildItem $OutDir -Filter 'slide-*.png' -ErrorAction SilentlyContinue | Remove-Item -Force
$Height = [int]($Width * 9 / 16)
$app = New-Object -ComObject PowerPoint.Application
$pres = $null
try {
  # Open(FileName, ReadOnly, Untitled, WithWindow)
  $pres = $app.Presentations.Open($Pptx, -1, 0, 0)
  $n = 0
  foreach ($s in $pres.Slides) {
    $n++
    $f = Join-Path $OutDir ('slide-{0:D2}.png' -f $s.SlideIndex)
    $s.Export($f, 'PNG', $Width, $Height)
  }
  Write-Output "rendered $n"
}
finally {
  if ($pres) { $pres.Close() }
  if ($app.Presentations.Count -eq 0) { $app.Quit() }
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
