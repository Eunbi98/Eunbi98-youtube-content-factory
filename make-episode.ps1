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

Write-Host "[1/3] 최신 코드 확인" -ForegroundColor Cyan
git fetch origin
git switch $branch
git pull --ff-only origin $branch

$episodePath = Join-Path "projects\episodes" $episodeId
$episodeJson = Join-Path $episodePath "episode.json"
if (-not (Test-Path $episodeJson)) {
    throw "에피소드 파일을 찾을 수 없습니다: $episodeJson"
}

Write-Host "[2/3] 에피소드 확인: $episodeId" -ForegroundColor Cyan
Write-Host "[3/3] 영상 제작 시작" -ForegroundColor Green
py factory_runner.py --episode $episodeId --rebuild-timeline

if ($LASTEXITCODE -ne 0) {
    throw "Factory Runner가 실패했습니다."
}

Write-Host "완료: projects\output\$episodeId.mp4" -ForegroundColor Green
