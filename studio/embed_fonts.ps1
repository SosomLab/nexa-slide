# PowerPoint COM 으로 PPTX 를 "글꼴 포함"으로 다시 저장한다(embed_fonts.py 가 부른다).
#   pwsh -NoProfile -File studio/embed_fonts.ps1 -Pptx out/intro.pptx -Out out/intro-fonts.pptx
# PowerPoint 는 설치된 TrueType 글꼴 중 포함이 허용된 것만 넣는다(OS/2 fsType). 받는 쪽은 글꼴을 설치하지 않아도 같은 모양으로 본다.
param(
  [Parameter(Mandatory = $true)][string]$Pptx,
  [Parameter(Mandatory = $true)][string]$Out
)
$ErrorActionPreference = 'Stop'
$Pptx = (Resolve-Path $Pptx).Path
$Out = [System.IO.Path]::GetFullPath($Out)
if (Test-Path $Out) { Remove-Item $Out -Force }
$app = New-Object -ComObject PowerPoint.Application
$pres = $null
try {
  # Open(FileName, ReadOnly, Untitled, WithWindow)
  $pres = $app.Presentations.Open($Pptx, -1, 0, 0)
  # SaveAs(FileName, ppSaveAsOpenXMLPresentation = 24, EmbedTrueTypeFonts = msoTrue)
  $pres.SaveAs($Out, 24, -1)
  Write-Output "embedded $Out"
}
finally {
  if ($pres) { $pres.Close() }
  if ($app.Presentations.Count -eq 0) { $app.Quit() }
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($app) | Out-Null
}
