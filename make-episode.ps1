param(
    [Parameter(Mandatory=$true, Position=0)]
    [string]$Episode
)

$ErrorActionPreference = "Stop"
$branch = "feature/release-5-director-engine"

$episodeId = $Episode.Trim().ToLower()
if ($episodeId -notmatch '^ep\d+$') {
    if ($episodeId -match '^\d+$') {
        $episodeId = "ep" + ([int]$episodeId).ToString('000')
    } else {
        throw "Episode 형식은 ep035 또는 035처럼 입력하세요."
    }
}

Write-Host "[1/4] 최신 코드 확인" -ForegroundColor Cyan
git fetch origin
git switch $branch
git pull --ff-only origin $branch

$episodePath = Join-Path "projects\episodes" $episodeId
$episodeJson = Join-Path $episodePath "episode.json"
if (-not (Test-Path $episodeJson)) {
    throw "에피소드 파일을 찾을 수 없습니다: $episodeJson"
}

Write-Host "[2/4] 수동 미디어 연결: $episodeId" -ForegroundColor Cyan
$assetsPath = Join-Path $episodePath "assets"
New-Item -ItemType Directory -Force -Path $assetsPath | Out-Null

$copiedCount = 0
$mediaSources = @(
    @{
        Path = (Join-Path $episodePath "images")
        Patterns = @("*.jpg", "*.jpeg", "*.png", "*.webp")
    },
    @{
        Path = (Join-Path $episodePath "video")
        Patterns = @("*.mp4", "*.mov", "*.webm")
    }
)

foreach ($source in $mediaSources) {
    if (-not (Test-Path $source.Path)) {
        continue
    }

    foreach ($pattern in $source.Patterns) {
        Get-ChildItem -Path $source.Path -Filter $pattern -File -ErrorAction SilentlyContinue | ForEach-Object {
            $destination = Join-Path $assetsPath $_.Name
            Copy-Item -LiteralPath $_.FullName -Destination $destination -Force
            Write-Host "  연결: $($_.Name) -> assets" -ForegroundColor DarkGray
            $copiedCount++
        }
    }
}

if ($copiedCount -gt 0) {
    Write-Host "  수동 미디어 $copiedCount개 연결 완료" -ForegroundColor Green
} else {
    Write-Host "  images/video 폴더의 수동 미디어가 없어 기존 assets를 사용합니다." -ForegroundColor Yellow
}

Write-Host "[3/4] 에피소드 확인: $episodeId" -ForegroundColor Cyan
Write-Host "[4/4] 영상 제작 시작" -ForegroundColor Green
py factory_runner.py --episode $episodeId --rebuild-timeline

if ($LASTEXITCODE -ne 0) {
    throw "Factory Runner가 실패했습니다."
}

Write-Host "완료: projects\output\$episodeId.mp4" -ForegroundColor Green
