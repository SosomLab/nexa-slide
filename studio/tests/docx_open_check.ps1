# DOCX 를 Word 로 열어 본다(페이지 편집기 PG-062 - 내보낸 DOCX 가 Word 에서 열리는지 · 쪽 수 · 문단 수 · 표 수 · 머리말 글). 결과는 JSON 한 줄.
#   pwsh -NoProfile -File studio/tests/docx_open_check.ps1 -Docx <파일.docx> [-Out <결과.json>]
# - 매크로·이벤트를 끄고(AutomationSecurity 3 · 이벤트 없음) 읽기 전용으로 열고, 저장하지 않고 닫는다.
# - 사용자가 Word 를 띄워 두었으면 건드리지 않는다: 자동화가 그 창에 붙을 수 있으므로 종료 코드 99(판정 불가, verify 의 SKIP)로 끝낸다.
# - 종료 코드: 0 = 열림 · 1 = 열지 못함 · 99 = 판정 불가(Word 없음 · 사용자 Word 실행 중 · 파일 없음).
# 이 파일은 BOM 이 있어야 pwsh 가 한글 주석을 바르게 읽는다.
param([Parameter(Mandatory = $true)][string]$Docx, [string]$Out = "")
$ErrorActionPreference = "Stop"
function Emit($o, $code) {
  $j = ConvertTo-Json -InputObject $o -Compress -Depth 4
  if ($Out) { [System.IO.File]::WriteAllText($Out, $j, [System.Text.UTF8Encoding]::new($false)) }
  [Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
  Write-Output $j
  exit $code
}
$path = [System.IO.Path]::GetFullPath($Docx)
if (-not (Test-Path -LiteralPath $path)) { Emit ([ordered]@{ ok = $false; skip = "파일 없음: $path" }) 99 }
if (Get-Process WINWORD -ErrorAction SilentlyContinue) { Emit ([ordered]@{ ok = $false; skip = "사용자 Word 가 실행 중 - 건드리지 않는다" }) 99 }
try { $w = New-Object -ComObject Word.Application } catch { Emit ([ordered]@{ ok = $false; skip = "Word 없음(COM 등록 없음)" }) 99 }
$res = [ordered]@{ ok = $false; file = $path }
try {
  $w.Visible = $false; $w.DisplayAlerts = 0
  $w.AutomationSecurity = 3  # msoAutomationSecurityForceDisable - 문서의 매크로가 돌지 않게
  try { $w.WordBasic.DisableAutoMacros(1) } catch { }
  $d = $w.Documents.Open($path, $false, $true, $false)  # ConfirmConversions=false · ReadOnly=true · AddToRecentFiles=false
  $res.pages = $d.ComputeStatistics(2)       # wdStatisticPages
  $res.paragraphs = $d.Paragraphs.Count
  $res.tables = $d.Tables.Count
  $res.sections = $d.Sections.Count
  $res.inlineShapes = $d.InlineShapes.Count
  $res.shapes = $d.Shapes.Count              # 떠 있는 도형·글 상자(본문 이야기)
  # 표마다 테두리 선 종류(0 = 없음) - 위·왼쪽·아래·오른쪽·가로 안쪽·세로 안쪽, 앞에서 5개까지
  $bds = @()
  for ($k = 1; $k -le [Math]::Min(5, $d.Tables.Count); $k++) {
    $tb = $d.Tables.Item($k).Borders
    # 칸마다 위·왼쪽·아래·오른쪽 선 종류 "행,열:T L B R" - 표 전체 값은 칸마다 다르면 9999999(정의 안 됨)라 눈에 보이는 선은 칸 값으로 본다
    $cl = @(); foreach ($c in $d.Tables.Item($k).Range.Cells) { if ($cl.Count -lt 40) { $cb = $c.Borders; $cl += ("{0},{1}:{2} {3} {4} {5}" -f $c.RowIndex, $c.ColumnIndex, $cb.Item(-1).LineStyle, $cb.Item(-2).LineStyle, $cb.Item(-3).LineStyle, $cb.Item(-4).LineStyle) } }
    $bds += [ordered]@{ top = $tb.Item(-1).LineStyle; left = $tb.Item(-2).LineStyle; bottom = $tb.Item(-3).LineStyle; right = $tb.Item(-4).LineStyle; h = $tb.Item(-5).LineStyle; v = $tb.Item(-6).LineStyle; cells = $cl }
  }
  $res.borders = $bds
  $res.header = ([string]$d.Sections.Item(1).Headers.Item(1).Range.Text).Trim()
  $res.footer = ([string]$d.Sections.Item(1).Footers.Item(1).Range.Text).Trim()
  # 번호 목록의 실제 번호 글(1. 2. a. …)과 제목 문단의 스타일·글자 크기 - 앞에서 40개까지
  $lists = @(); $heads = @(); $n = $d.Paragraphs.Count
  for ($k = 1; $k -le $n -and ($lists.Count -lt 40 -or $heads.Count -lt 20); $k++) {
    $p = $d.Paragraphs.Item($k)
    $t = ([string]$p.Range.Text).Trim()
    try { if ($p.Range.ListFormat.ListType -ne 0 -and $lists.Count -lt 40) { $lists += [ordered]@{ n = $k; s = [string]$p.Range.ListFormat.ListString; lv = $p.Range.ListFormat.ListLevelNumber; t = $t.Substring(0, [Math]::Min(20, $t.Length)) } } } catch { }
    $st = [string]$p.Style.NameLocal
    if ($heads.Count -lt 20 -and ($st -match '^(Heading|제목|Title)' -or $p.OutlineLevel -lt 10)) { $heads += [ordered]@{ n = $k; style = $st; size = $p.Range.Font.Size; t = $t.Substring(0, [Math]::Min(20, $t.Length)) } }
  }
  # 음영(배경색)이 있는 문단 - 앞에서 20개까지 · c = RGB 16진(Word 는 BGR 정수 · -16777216 = 자동)
  $shades = @()
  for ($k = 1; $k -le $n -and $shades.Count -lt 20; $k++) {
    $p = $d.Paragraphs.Item($k); $bgc = [int]$p.Shading.BackgroundPatternColor
    if ($bgc -ne -16777216 -and $bgc -ne 16777215) { $t = ([string]$p.Range.Text).Trim(); $shades += [ordered]@{ n = $k; c = ("{0:X2}{1:X2}{2:X2}" -f ($bgc -band 255), (($bgc -shr 8) -band 255), (($bgc -shr 16) -band 255)); t = $t.Substring(0, [Math]::Min(20, $t.Length)) } }
  }
  $res.shades = $shades
  $res.lists = $lists; $res.heads = $heads
  $res.ok = $true
  $d.Close(0)  # wdDoNotSaveChanges
} catch {
  $res.error = $_.Exception.Message
} finally {
  try { $w.Quit(0) } catch { }
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($w) | Out-Null
}
if ($res.ok) { Emit $res 0 } else { Emit $res 1 }
