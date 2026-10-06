from __future__ import annotations

import argparse
import hashlib
import json
import shutil
import sys
from pathlib import Path
from typing import Any


CURRENT_FILE = Path(__file__).resolve()
PROJECT_ROOT = CURRENT_FILE.parents[3]

EPISODES_DIR = (
    PROJECT_ROOT
    / "projects"
    / "episodes"
)

REMOTION_PUBLIC_DIR = (
    PROJECT_ROOT
    / "projects"
    / "remotion"
    / "public"
)


class QuizAssetsSyncError(RuntimeError):
    """퀴즈 Remotion 에셋 동기화 실패."""


def normalize_episode_id(
    raw_episode_id: str,
) -> str:
    value = raw_episode_id.strip().lower()

    if value.startswith("ep"):
        number_text = value[2:]
    else:
        number_text = value

    if not number_text.isdigit():
        raise QuizAssetsSyncError(
            "에피소드 형식이 올바르지 않습니다. "
            "예: ep010 또는 010"
        )

    return f"ep{int(number_text):03d}"


def load_json(
    path: Path,
) -> dict[str, Any]:
    if not path.exists():
        raise QuizAssetsSyncError(
            f"파일이 없습니다: {path}"
        )

    if not path.is_file():
        raise QuizAssetsSyncError(
            f"파일 경로가 아닙니다: {path}"
        )

    try:
        with path.open(
            "r",
            encoding="utf-8",
        ) as file:
            data = json.load(file)
    except json.JSONDecodeError as error:
        raise QuizAssetsSyncError(
            f"JSON 형식이 올바르지 않습니다: "
            f"{path}\n{error}"
        ) from error

    if not isinstance(data, dict):
        raise QuizAssetsSyncError(
            f"JSON 최상위 값은 객체여야 합니다: "
            f"{path}"
        )

    return data


def validate_timeline(
    timeline: dict[str, Any],
    episode_id: str,
) -> None:
    timeline_episode_id = timeline.get(
        "episodeId"
    )

    if timeline_episode_id != episode_id:
        raise QuizAssetsSyncError(
            "Timeline episodeId가 일치하지 않습니다. "
            f"예상: {episode_id}, "
            f"실제: {timeline_episode_id}"
        )

    required_fields = (
        "title",
        "fps",
        "width",
        "height",
        "totalDuration",
        "theme",
        "scenes",
    )

    missing_fields = [
        field
        for field in required_fields
        if field not in timeline
    ]

    if missing_fields:
        raise QuizAssetsSyncError(
            "Timeline 필수 필드가 없습니다: "
            + ", ".join(missing_fields)
        )

    scenes = timeline.get("scenes")

    if not isinstance(scenes, list):
        raise QuizAssetsSyncError(
            "Timeline scenes는 배열이어야 합니다."
        )

    if not scenes:
        raise QuizAssetsSyncError(
            "Timeline에 장면이 없습니다."
        )

    scene_ids: set[str] = set()

    for index, scene in enumerate(
        scenes,
        start=1,
    ):
        if not isinstance(scene, dict):
            raise QuizAssetsSyncError(
                f"{index}번째 장면이 객체가 아닙니다."
            )

        scene_id = scene.get("id")

        if (
            not isinstance(scene_id, str)
            or not scene_id.strip()
        ):
            raise QuizAssetsSyncError(
                f"{index}번째 장면의 id가 "
                "올바르지 않습니다."
            )

        if scene_id in scene_ids:
            raise QuizAssetsSyncError(
                f"장면 ID가 중복되었습니다: "
                f"{scene_id}"
            )

        scene_ids.add(scene_id)

        media = scene.get("media")

        if not isinstance(media, dict):
            raise QuizAssetsSyncError(
                f"{scene_id}: media가 없습니다."
            )

        media_type = media.get("type")

        if media_type not in {
            "color",
            "image",
            "video",
        }:
            raise QuizAssetsSyncError(
                f"{scene_id}: 지원하지 않는 "
                f"media.type입니다: {media_type}"
            )


def calculate_sha256(
    path: Path,
) -> str:
    digest = hashlib.sha256()

    with path.open("rb") as file:
        while True:
            chunk = file.read(1024 * 1024)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def copy_atomic(
    source_path: Path,
    destination_path: Path,
) -> None:
    destination_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    temporary_path = destination_path.with_suffix(
        destination_path.suffix + ".tmp"
    )

    shutil.copy2(
        source_path,
        temporary_path,
    )

    temporary_path.replace(
        destination_path
    )


def sync_quiz_assets(
    episode_id: str,
) -> tuple[Path, Path, int, float]:
    source_episode_dir = (
        EPISODES_DIR
        / episode_id
    )

    destination_episode_dir = (
        REMOTION_PUBLIC_DIR
        / episode_id
    )

    source_timeline_path = (
        source_episode_dir
        / "timeline.json"
    )

    destination_timeline_path = (
        destination_episode_dir
        / "timeline.json"
    )

    timeline = load_json(
        source_timeline_path
    )

    validate_timeline(
        timeline=timeline,
        episode_id=episode_id,
    )

    copy_atomic(
        source_path=source_timeline_path,
        destination_path=(
            destination_timeline_path
        ),
    )

    source_hash = calculate_sha256(
        source_timeline_path
    )
    destination_hash = calculate_sha256(
        destination_timeline_path
    )

    if source_hash != destination_hash:
        raise QuizAssetsSyncError(
            "동기화된 Timeline 파일이 "
            "원본과 일치하지 않습니다."
        )

    copied_timeline = load_json(
        destination_timeline_path
    )

    validate_timeline(
        timeline=copied_timeline,
        episode_id=episode_id,
    )

    scene_count = len(
        copied_timeline["scenes"]
    )

    total_duration = float(
        copied_timeline["totalDuration"]
    )

    return (
        source_timeline_path,
        destination_timeline_path,
        scene_count,
        total_duration,
    )


def create_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "퀴즈 Timeline과 에셋을 "
            "Remotion public 폴더에 동기화합니다."
        )
    )

    parser.add_argument(
        "--episode-id",
        default="ep010",
        help="동기화할 에피소드 ID",
    )

    return parser


def main() -> int:
    parser = create_parser()
    args = parser.parse_args()

    try:
        episode_id = normalize_episode_id(
            args.episode_id
        )

        (
            source_path,
            destination_path,
            scene_count,
            total_duration,
        ) = sync_quiz_assets(
            episode_id
        )

        print("=" * 60)
        print(
            " YouTube Content Factory "
            "- Quiz Assets Sync"
        )
        print("=" * 60)
        print(f"에피소드: {episode_id}")
        print(f"원본: {source_path}")
        print(f"복사: {destination_path}")
        print(f"장면 수: {scene_count}")
        print(
            f"전체 길이: "
            f"{total_duration:.1f}초"
        )
        print("미디어 파일: 필요 없음")
        print("=" * 60)
        print("Quiz Assets Sync 성공")

        return 0

    except (
        OSError,
        QuizAssetsSyncError,
        ValueError,
    ) as error:
        print("=" * 60)
        print(" Quiz Assets Sync 실패")
        print("=" * 60)
        print(error)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())