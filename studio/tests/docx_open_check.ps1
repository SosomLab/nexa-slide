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
