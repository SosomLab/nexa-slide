# 엑셀(COM)로 통합 문서를 열어 모두 다시 계산한 뒤 내용을 JSON 으로 - xlsm_crosscheck.py 가 부른다(Windows + Excel 만).
# 탭마다 사용 범위의 수식(Formula2)·계산값(Value2, 다시 계산 전·후)·숨긴 행·열·자동 필터, 문서 이름 정의, VBA 프로젝트 여부.
# 매크로는 자동화로 연 문서라 켜진다(AutomationSecurity 1) - VBA 사용자 함수도 엑셀이 계산한다.
param([string]$Path, [string]$Out)
$ErrorActionPreference = "Stop"
function Grid($v, $rows, $cols) {
  $g = New-Object System.Collections.ArrayList
  if ($rows -eq 1 -and $cols -eq 1) { [void]$g.Add(@(,$v)); return ,$g }
  for ($r = 1; $r -le $rows; $r++) {
    $row = New-Object System.Collections.ArrayList
    for ($c = 1; $c -le $cols; $c++) { [void]$row.Add($v.GetValue($r, $c)) }
    [void]$g.Add($row)
  }
  return ,$g
}
$xl = New-Object -ComObject Excel.Application
$xl.Visible = $false; $xl.DisplayAlerts = $false; $xl.AutomationSecurity = 1; $xl.EnableEvents = $false
try {
  $wb = $xl.Workbooks.Open($Path, 0, $true)
  $res = [ordered]@{ sheets = New-Object System.Collections.ArrayList; names = New-Object System.Collections.ArrayList; vba = [bool]$wb.HasVBProject }
  $before = @{}
  foreach ($ws in $wb.Worksheets) { $u = $ws.UsedRange; $before[$ws.Name] = Grid $u.Value2 $u.Rows.Count $u.Columns.Count }
  $xl.CalculateFull()
  foreach ($ws in $wb.Worksheets) {
    $u = $ws.UsedRange; $nr = $u.Rows.Count; $nc = $u.Columns.Count
    $hr = New-Object System.Collections.ArrayList; $hc = New-Object System.Collections.ArrayList
    for ($r = 1; $r -le ($u.Row + $nr - 1); $r++) { if ($ws.Rows.Item($r).Hidden) { [void]$hr.Add($r) } }
    for ($c = 1; $c -le ($u.Column + $nc - 1); $c++) { if ($ws.Columns.Item($c).Hidden) { [void]$hc.Add($c) } }
    $af = $null
    if ($ws.AutoFilterMode) {
      $cols = New-Object System.Collections.ArrayList
      $fs = $ws.AutoFilter.Filters
      for ($i = 1; $i -le $fs.Count; $i++) { $f = $fs.Item($i); if ($f.On) { $c1 = $null; $c2 = $null; try { $c1 = $f.Criteria1 } catch {}; try { $c2 = $f.Criteria2 } catch {}; [void]$cols.Add([ordered]@{ i = $i; op = $f.Operator; c1 = $c1; c2 = $c2 }) } }
      $af = [ordered]@{ ref = $ws.AutoFilter.Range.Address($false, $false); cols = $cols }
    }
    $shp = New-Object System.Collections.ArrayList  # 그림·도형·단추 - 종류·자리·크기(pt, 0.1 반올림)·연결한 매크로
    foreach ($s in $ws.Shapes) { $m = ""; try { $m = $s.OnAction } catch {}; [void]$shp.Add(("{0}|{1}|{2:N1},{3:N1}|{4:N1}x{5:N1}|{6}" -f $s.Name, $s.Type, $s.Left, $s.Top, $s.Width, $s.Height, $m)) }
    [void]$res.sheets.Add([ordered]@{ shapes = $shp; colW = (1..[math]::Min(60, $u.Column + $nc - 1) | % { $ws.Columns.Item($_).Width }); rowH = (1..[math]::Min(300, $u.Row + $nr - 1) | % { $ws.Rows.Item($_).Height }); name = $ws.Name; code = $ws.CodeName; visible = $ws.Visible; first = $u.Address($false, $false).Split(":")[0]; rows = $nr; cols = $nc
      f = (Grid $u.Formula2 $nr $nc); v = (Grid $u.Value2 $nr $nc); v0 = $before[$ws.Name]; hiddenRows = $hr; hiddenCols = $hc; filter = $af })
  }
  foreach ($n in $wb.Names) { [void]$res.names.Add([ordered]@{ name = $n.Name; ref = $n.RefersTo; visible = $n.Visible }) }
  $wb.Close($false)
  [System.IO.File]::WriteAllText($Out, ($res | ConvertTo-Json -Depth 8 -Compress), (New-Object System.Text.UTF8Encoding $false))
} finally { $xl.Quit(); [System.Runtime.InteropServices.Marshal]::ReleaseComObject($xl) | Out-Null }
