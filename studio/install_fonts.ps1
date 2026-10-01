# 추천 글꼴(modern 프리셋)을 내려받아 현재 사용자에게 설치한다(관리자 권한 불필요).
#   pwsh -NoProfile -File studio/install_fonts.ps1
#
# 글꼴(모두 SIL Open Font License 1.1 — 무료, 재배포·임베드 가능)
#   Pretendard 1.3.9        본문(한글·라틴) — 정적 굵기 파일(PowerPoint는 가변 글꼴의 굵기 축을 제대로 못 쓴다)
#   JetBrains Mono 2.304    코드(라틴) — 0/O, 1/l/I, 5/S, rn/m 구분이 뚜렷
#   D2Coding 1.3.2          코드 안의 한글(고정폭, 한글 2칸 = 라틴 1칸 × 2)
# 내려받은 파일은 엔진 저장소의 .cache/fonts 에 둔다(git 제외). PowerPoint·브라우저는 설치 후 다시 열어야 보인다.
$ErrorActionPreference = 'Stop'
$engine = (Resolve-Path "$PSScriptRoot/..").Path
$cache = Join-Path $engine '.cache/fonts'
New-Item -ItemType Directory -Force $cache | Out-Null
$src = @(
  @{ name = 'Pretendard'; url = 'https://github.com/orioncactus/pretendard/releases/download/v1.3.9/Pretendard-1.3.9.zip';
     pick = 'public/static/Pretendard-(Regular|Medium|SemiBold|Bold|ExtraBold)\.otf$' },
  @{ name = 'JetBrainsMono'; url = 'https://github.com/JetBrains/JetBrainsMono/releases/download/v2.304/JetBrainsMono-2.304.zip';
     pick = 'fonts/ttf/JetBrainsMono-(Regular|Medium|SemiBold|Bold|Italic|BoldItalic)\.ttf$' },
  @{ name = 'D2Coding'; url = 'https://github.com/naver/d2codingfont/releases/download/VER1.3.2/D2Coding-Ver1.3.2-20180524.zip';
     pick = 'D2Coding/D2Coding(Bold)?-Ver1\.3\.2-20180524\.ttf$' }
)
$dest = Join-Path $env:LOCALAPPDATA 'Microsoft/Windows/Fonts'
New-Item -ItemType Directory -Force $dest | Out-Null
$reg = 'HKCU:\Software\Microsoft\Windows NT\CurrentVersion\Fonts'
Add-Type -AssemblyName System.IO.Compression.FileSystem
foreach ($f in $src) {
  $zip = Join-Path $cache "$($f.name).zip"
  if (-not (Test-Path $zip)) { Write-Output "내려받기: $($f.url)"; Invoke-WebRequest $f.url -OutFile $zip }
  $z = [System.IO.Compression.ZipFile]::OpenRead($zip)
  try {
    foreach ($e in $z.Entries | Where-Object { $_.FullName -replace '\\', '/' -match $f.pick }) {
      $out = Join-Path $dest $e.Name
      if (-not (Test-Path $out)) { [System.IO.Compression.ZipFileExtensions]::ExtractToFile($e, $out, $true) }
      $kind = if ($e.Name -like '*.otf') { 'OpenType' } else { 'TrueType' }
      $label = ($e.Name -replace '\.(otf|ttf)$', '') -replace '-Ver1\.3\.2-20180524', ''
      Set-ItemProperty -Path $reg -Name "$label ($kind)" -Value $out
      Write-Output "설치: $($e.Name)"
    }
  } finally { $z.Dispose() }
}
Write-Output '완료 — PowerPoint·브라우저를 다시 열면 적용된다.'
