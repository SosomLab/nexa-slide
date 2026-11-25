# Word(COM)로 가져오기 시험용 문서를 만든다(페이지 편집기 PG-100 가져오기 - Word 가 실제로 만든 XML 을 import_docx 가 옮기는지).
#   pwsh -NoProfile -File studio/tests/docx_make_word.ps1 -Out <파일.docx>
# 들어가는 것: 제목 1·제목 2 문단 · 굵게·빨강·형광펜 · 글머리·번호 목록 2단계 · 3×3 표(가로 병합 1·세로 병합 1) · 그림 1(글자처럼) · 쪽 나누기
#             · 머리말 글 + 쪽 번호 필드 · 각주 1 · 글 상자 1(떠 있는 개체).
# 사용자가 Word 를 띄워 두었으면 건드리지 않고 99(판정 불가), Word 가 없으면 99. 우리가 띄운 Word 만 끝낸다. 매크로는 끈다.
# 이 파일은 BOM 이 있어야 pwsh 가 한글 주석을 바르게 읽는다.
param([Parameter(Mandatory = $true)][string]$Out)
$ErrorActionPreference = "Stop"
$path = [System.IO.Path]::GetFullPath($Out)
if (Get-Process WINWORD -ErrorAction SilentlyContinue) { Write-Output "SKIP 사용자 Word 가 실행 중"; exit 99 }
try { $w = New-Object -ComObject Word.Application } catch { Write-Output "SKIP Word 없음"; exit 99 }
try {
  $w.Visible = $false; $w.DisplayAlerts = 0; $w.AutomationSecurity = 3
  $d = $w.Documents.Add()
  $s = $w.Selection
  $s.Style = $d.Styles.Item(-2); $s.TypeText("제목 하나"); $s.TypeParagraph()
  $s.Style = $d.Styles.Item(-3); $s.TypeText("제목 둘"); $s.TypeParagraph()
  $s.Style = $d.Styles.Item(-1)
  $s.TypeText("보통 ")
  $s.Font.Bold = 1; $s.TypeText("굵게"); $s.Font.Bold = 0
  $s.Font.Color = 255; $s.TypeText(" 빨강"); $s.Font.Color = -16777216
  $a = $s.Start; $s.TypeText(" 형광"); $d.Range($a, $s.Start).HighlightColorIndex = 7
  $s.TypeParagraph()
  # 글머리 2단계 → 번호 2단계
  $s.Range.ListFormat.ApplyBulletDefault(); $s.TypeText("글머리 하나"); $s.TypeParagraph()
  $s.Range.SetListLevel(2); $s.TypeText("글머리 둘째 단계"); $s.TypeParagraph()
  $s.Range.ListFormat.RemoveNumbers(); $s.TypeParagraph()
  $s.Range.ListFormat.ApplyNumberDefault(); $s.TypeText("번호 하나"); $s.TypeParagraph()
  $s.Range.SetListLevel(2); $s.TypeText("번호 둘째 단계"); $s.TypeParagraph()
  $s.Range.ListFormat.RemoveNumbers()
  $s.TypeText("표 앞 문단"); $s.TypeParagraph()
  # 3×3 표 - (1,1)+(1,2) 가로 병합 · (2,3)+(3,3) 세로 병합
  $t = $d.Tables.Add($s.Range, 3, 3)
  for ($r = 1; $r -le 3; $r++) { for ($c = 1; $c -le 3; $c++) { $t.Cell($r, $c).Range.Text = "칸$r$c" } }
  $t.Cell(1, 1).Merge($t.Cell(1, 2))
  $t.Cell(2, 3).Merge($t.Cell(3, 3))
  $s.EndKey(6) | Out-Null
  $s.TypeParagraph(); $s.TypeText("그림 앞"); $s.TypeParagraph()
  # 그림 - 작은 png 를 만들어 글자처럼 넣는다
  Add-Type -AssemblyName System.Drawing
  $png = [System.IO.Path]::ChangeExtension($path, ".png")
  $bmp = New-Object System.Drawing.Bitmap 120, 60
  $g = [System.Drawing.Graphics]::FromImage($bmp); $g.Clear([System.Drawing.Color]::FromArgb(200, 85, 61)); $g.Dispose()
  $bmp.Save($png, [System.Drawing.Imaging.ImageFormat]::Png); $bmp.Dispose()
  $s.InlineShapes.AddPicture($png) | Out-Null
  $s.TypeParagraph()
  $s.TypeText("각주가 붙는 문단")
  $fn = $d.Footnotes.Add($s.Range); $fn.Range.Text = "각주 글"
  $s.EndKey(6) | Out-Null
  $s.TypeParagraph()
  $s.InsertBreak(7)  # wdPageBreak
  $s.TypeText("둘째 쪽 문단")
  # 머리말 글 + 쪽 번호 필드
  $h = $d.Sections.Item(1).Headers.Item(1).Range
  $h.Text = "머리말 글 "
  $h.Collapse(0)
  $d.Fields.Add($h, 33) | Out-Null  # wdFieldPage
  # 글 상자(떠 있는 개체)
  $tb = $d.Shapes.AddTextbox(1, 300, 120, 150, 50); $tb.TextFrame.TextRange.Text = "글 상자 글"
  $d.SaveAs2($path, 16)  # wdFormatXMLDocument
  $d.Close(0)
  Remove-Item -LiteralPath $png -ErrorAction SilentlyContinue
  Write-Output "OK $path"
} catch {
  Write-Output "FAIL $($_.Exception.Message)"
  exit 1
} finally {
  try { $w.Quit(0) } catch { }
  [System.Runtime.InteropServices.Marshal]::ReleaseComObject($w) | Out-Null
}
