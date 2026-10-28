# 엑셀 파일의 도형(그림·도형 묶음)을 PNG 로 떠낸다 - sheet_theme.py import 가 부른다(Windows + Excel 이 있을 때만).
# 원본은 읽기 전용으로 열고 저장하지 않는다. 결과: OutDir\shape-<시트번호>-<순번>.png 와 OutDir\shapes.json(UTF-8, 도형마다 시트·이름·종류·셀·위치·크기 pt·글).
# 한글 경로·글이 콘솔 코드 페이지에 깨지지 않게 결과는 파일로 쓴다. 이 파일은 BOM 이 있어야 pwsh 가 한글 주석을 바르게 읽는다.
param([Parameter(Mandatory = $true)][string]$Xlsx, [Parameter(Mandatory = $true)][string]$OutDir, [double]$Zoom = 4)
$ErrorActionPreference = "Stop"
New-Item -ItemType Directory -Force $OutDir | Out-Null
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.ScreenUpdating = $false
$out = @()
try {
  $wb = $null
  for ($t = 0; $t -lt 5 -and -not $wb; $t++) {  # 막 띄운 Excel 이 준비되기 전에는 Open 이 null 을 돌려줄 때가 있다
    try { $wb = $xl.Workbooks.Open($Xlsx, 0, $true) } catch { }
    if (-not $wb) { Start-Sleep -Milliseconds 800 }
  }
  if (-not $wb) { throw "엑셀 파일을 열지 못했다: $Xlsx" }
  for ($si = 1; $si -le 255; $si++) {  # pwsh 7 에서 COM 컬렉션의 Count·foreach 가 0 으로 보일 때가 있어 Item 이 실패할 때까지 번호로 돈다
    try { $ws = $wb.Worksheets.Item($si) } catch { break }
    if ($ws.Visible -ne -1) { continue }
    $n = $ws.Shapes.Count
    for ($k = 1; $k -le $n; $k++) {
      $sh = $ws.Shapes.Item($k)
      $text = ""
      try { if ($sh.TextFrame2.HasText) { $text = $sh.TextFrame2.TextRange.Text } } catch { }
      $size = 0; $bold = $false
      try { if ($text) { $size = $sh.TextFrame2.TextRange.Font.Size; $bold = [bool]$sh.TextFrame2.TextRange.Font.Bold } } catch { }
      $png = ""
      if (-not $text -and $sh.Type -ne 9 -and $sh.Width -gt 4 -and $sh.Height -gt 4) {  # 9 = 선 - 그림·도형 묶음만 떠낸다
        try {
          # 벡터(xlPicture)로 복사해 4배 크기 차트에 붙여 PNG 로 - 비트맵 복사는 화면 해상도라 작고, 활성화하지 않은 차트는 빈 그림이 된다
          $sh.CopyPicture(1, -4147)
          $co = $ws.ChartObjects().Add(0, 0, $sh.Width * $Zoom, $sh.Height * $Zoom)
          $co.Activate() | Out-Null
          $co.Chart.ChartArea.Format.Line.Visible = 0
          $co.Chart.ChartArea.Format.Fill.Visible = 0
          $co.Chart.Paste() | Out-Null
          $p = $co.Chart.Shapes.Item($co.Chart.Shapes.Count)
          $p.LockAspectRatio = 0; $p.Left = 0; $p.Top = 0; $p.Width = $sh.Width * $Zoom; $p.Height = $sh.Height * $Zoom
          $png = Join-Path $OutDir ("shape-{0}-{1}.png" -f $si, $k)
          $co.Chart.Export($png, "PNG") | Out-Null
          $co.Delete()
        } catch { $png = "" }
      }
      $out += [ordered]@{ sheet = $si; sheetName = $ws.Name; name = $sh.Name; type = $sh.Type; cell = $sh.TopLeftCell.Address($false, $false);
        left = [math]::Round($sh.Left, 1); top = [math]::Round($sh.Top, 1); width = [math]::Round($sh.Width, 1); height = [math]::Round($sh.Height, 1);
        text = $text; size = $size; bold = $bold; png = $png }
    }
  }
  $wb.Close($false)
} finally {
  $xl.Quit()
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null
}
[System.IO.File]::WriteAllText((Join-Path $OutDir "shapes.json"), (ConvertTo-Json -InputObject @($out) -Compress -Depth 4), [System.Text.UTF8Encoding]::new($false))
