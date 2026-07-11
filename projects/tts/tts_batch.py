from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tts_config import TTSConfig, TTSConfigError
from tts_engine import (
    EdgeTTSEngine,
    TTSEngineError,
    TTSGenerationResult,
)


class TTSBatchError(RuntimeError):
    """Timeline 기반 TTS 일괄 생성 오류입니다."""


@dataclass(frozen=True, slots=True)
class TimelineScene:
    scene_id: str
    narration: str


@dataclass(frozen=True, slots=True)
class TTSBatchResult:
    episode_id: str
    timeline_path: Path
    output_dir: Path
    generated_count: int
    reused_count: int
    total_count: int
    results: tuple[TTSGenerationResult, ...]


def load_timeline_scenes(
    timeline_path: Path,
) -> tuple[str, list[TimelineScene]]:
    resolved_path = timeline_path.resolve()

    if not resolved_path.exists():
        raise TTSBatchError(
            "Timeline 파일을 찾을 수 없습니다:\n"
            f"{resolved_path}"
        )

    if not resolved_path.is_file():
        raise TTSBatchError(
            "Timeline 경로가 파일이 아닙니다:\n"
            f"{resolved_path}"
        )

    try:
        with resolved_path.open(
            "r",
            encoding="utf-8",
        ) as file:
            timeline_data = json.load(file)

    except json.JSONDecodeError as exc:
        raise TTSBatchError(
            "Timeline JSON 형식이 올바르지 않습니다.\n"
            f"파일: {resolved_path}\n"
            f"위치: line {exc.lineno}, "
            f"column {exc.colno}\n"
            f"원인: {exc.msg}"
        ) from exc

    except OSError as exc:
        raise TTSBatchError(
            "Timeline 파일을 읽지 못했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc

    if not isinstance(timeline_data, dict):
        raise TTSBatchError(
            "Timeline 최상위 데이터는 객체여야 합니다."
        )

    episode_id = _read_episode_id(
        timeline_data=timeline_data,
        timeline_path=resolved_path,
    )

    raw_scenes = timeline_data.get("scenes")

    if not isinstance(raw_scenes, list):
        raise TTSBatchError(
            "Timeline의 scenes 필드가 배열이 아닙니다."
        )

    if not raw_scenes:
        raise TTSBatchError(
            "Timeline에 scene이 없습니다."
        )

    scenes: list[TimelineScene] = []
    seen_scene_ids: set[str] = set()

    for index, raw_scene in enumerate(
        raw_scenes,
        start=1,
    ):
        scene = _parse_scene(
            raw_scene=raw_scene,
            scene_number=index,
        )

        if scene.scene_id in seen_scene_ids:
            raise TTSBatchError(
                "중복된 scene id가 있습니다: "
                f"{scene.scene_id}"
            )

        seen_scene_ids.add(scene.scene_id)
        scenes.append(scene)

    return episode_id, scenes


def _read_episode_id(
    *,
    timeline_data: dict[str, Any],
    timeline_path: Path,
) -> str:
    raw_episode_id = timeline_data.get(
        "episodeId"
    )

    if isinstance(raw_episode_id, str):
        normalized = raw_episode_id.strip()

        if normalized:
            return normalized.lower()

    parent_name = timeline_path.parent.name.strip()

    if parent_name:
        return parent_name.lower()

    raise TTSBatchError(
        "Timeline에서 episodeId를 확인할 수 없습니다."
    )


def _parse_scene(
    *,
    raw_scene: Any,
    scene_number: int,
) -> TimelineScene:
    if not isinstance(raw_scene, dict):
        raise TTSBatchError(
            f"{scene_number}번째 scene이 "
            "객체 형식이 아닙니다."
        )

    raw_scene_id = raw_scene.get("id")

    if not isinstance(raw_scene_id, str):
        raise TTSBatchError(
            f"{scene_number}번째 scene의 "
            "id가 문자열이 아닙니다."
        )

    scene_id = raw_scene_id.strip()

    if not scene_id:
        raise TTSBatchError(
            f"{scene_number}번째 scene의 "
            "id가 비어 있습니다."
        )

    raw_narration = raw_scene.get(
        "narration"
    )

    if not isinstance(raw_narration, str):
        raise TTSBatchError(
            f"{scene_id}: narration 필드가 "
            "문자열이 아닙니다."
        )

    narration = " ".join(
        raw_narration
        .replace("\r", " ")
        .replace("\n", " ")
        .split()
    )

    if not narration:
        raise TTSBatchError(
            f"{scene_id}: narration이 "
            "비어 있습니다."
        )

    return TimelineScene(
        scene_id=scene_id,
        narration=narration,
    )


class TimelineTTSBatchGenerator:
    """
    Timeline의 모든 narration을 장면별 음성 파일로 변환합니다.
    """

    def __init__(
        self,
        *,
        engine: EdgeTTSEngine,
    ) -> None:
        self.engine = engine

    async def generate(
        self,
        *,
        timeline_path: Path,
        output_dir: Path | None = None,
    ) -> TTSBatchResult:
        episode_id, scenes = (
            load_timeline_scenes(
                timeline_path
            )
        )

        resolved_output_dir = (
            output_dir.resolve()
            if output_dir is not None
            else (
                timeline_path
                .resolve()
                .parent
                / "audio"
            )
        )

        resolved_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        results: list[
            TTSGenerationResult
        ] = []

        generated_count = 0
        reused_count = 0

        print("=" * 62)
        print(
            " YouTube Content Factory "
            "Release 6.3"
        )
        print(" Timeline TTS Batch Generation")
        print("=" * 62)
        print(
            f"{'episode':>16}: "
            f"{episode_id}"
        )
        print(
            f"{'timeline':>16}: "
            f"{timeline_path.resolve()}"
        )
        print(
            f"{'output':>16}: "
            f"{resolved_output_dir}"
        )
        print(
            f"{'scene_count':>16}: "
            f"{len(scenes)}"
        )
        print("-" * 62)

        for index, scene in enumerate(
            scenes,
            start=1,
        ):
            expected_path = (
                self.engine
                .config
                .build_scene_path(
                    output_dir=(
                        resolved_output_dir
                    ),
                    scene_id=scene.scene_id,
                )
            )

            existed_before = (
                expected_path.exists()
                and expected_path.stat().st_size
                > 0
                and not self.engine.config.overwrite
            )

            print(
                f"[{index}/{len(scenes)}] "
                f"{scene.scene_id}"
            )
            print(
                f"       대사: "
                f"{scene.narration}"
            )

            result = await self.engine.generate(
                scene_id=scene.scene_id,
                text=scene.narration,
                output_dir=resolved_output_dir,
            )

            results.append(result)

            if existed_before:
                reused_count += 1
            else:
                generated_count += 1

            print(
                f"       파일: "
                f"{result.output_path.name}"
            )
            print(
                f"       크기: "
                f"{result.file_size_bytes:,} bytes"
            )

        return TTSBatchResult(
            episode_id=episode_id,
            timeline_path=(
                timeline_path.resolve()
            ),
            output_dir=resolved_output_dir,
            generated_count=generated_count,
            reused_count=reused_count,
            total_count=len(results),
            results=tuple(results),
        )

    def generate_sync(
        self,
        *,
        timeline_path: Path,
        output_dir: Path | None = None,
    ) -> TTSBatchResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.generate(
                    timeline_path=timeline_path,
                    output_dir=output_dir,
                )
            )

        raise TTSBatchError(
            "이미 실행 중인 asyncio 이벤트 루프가 "
            "있습니다. 비동기 환경에서는 "
            "await generator.generate(...)를 "
            "사용하세요."
        )


def resolve_project_root() -> Path:
    return (
        Path(__file__)
        .resolve()
        .parents[2]
    )


def resolve_timeline_path(
    *,
    episode: str,
    timeline_argument: str | None,
) -> Path:
    if timeline_argument:
        return Path(timeline_argument)

    return (
        resolve_project_root()
        / "projects"
        / "episodes"
        / episode
        / "timeline.json"
    )


def resolve_output_dir(
    output_argument: str | None,
) -> Path | None:
    if not output_argument:
        return None

    return Path(output_argument)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Timeline narration을 읽어 "
            "장면별 TTS 파일을 생성합니다."
        )
    )

    parser.add_argument(
        "--episode",
        default="ep008",
        help=(
            "에피소드 ID입니다. "
            "기본값: ep008"
        ),
    )

    parser.add_argument(
        "--timeline",
        default=None,
        help=(
            "timeline.json 경로입니다. "
            "생략하면 에피소드 폴더의 "
            "timeline.json을 사용합니다."
        ),
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "음성 저장 폴더입니다. "
            "생략하면 timeline.json과 같은 "
            "폴더의 audio 폴더를 사용합니다."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "기존 음성 파일이 있어도 "
            "새로 생성합니다."
        ),
    )

    return parser


def print_summary(
    result: TTSBatchResult,
) -> None:
    print("-" * 62)
    print("[완료] Timeline TTS 일괄 생성")
    print(
        f"{'전체 장면':>16}: "
        f"{result.total_count}"
    )
    print(
        f"{'새로 생성':>16}: "
        f"{result.generated_count}"
    )
    print(
        f"{'기존 사용':>16}: "
        f"{result.reused_count}"
    )
    print(
        f"{'저장 폴더':>16}: "
        f"{result.output_dir}"
    )


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    timeline_path = resolve_timeline_path(
        episode=arguments.episode,
        timeline_argument=arguments.timeline,
    )

    output_dir = resolve_output_dir(
        arguments.output_dir
    )

    try:
        base_config = (
            TTSConfig.from_environment()
        )

        config = TTSConfig(
            provider=base_config.provider,
            language=base_config.language,
            voice=base_config.voice,
            rate=base_config.rate,
            volume=base_config.volume,
            pitch=base_config.pitch,
            audio_format=(
                base_config.audio_format
            ),
            scene_gap_ms=(
                base_config.scene_gap_ms
            ),
            overwrite=(
                arguments.overwrite
                or base_config.overwrite
            ),
        )

        engine = EdgeTTSEngine(
            config=config
        )

        generator = (
            TimelineTTSBatchGenerator(
                engine=engine
            )
        )

        result = generator.generate_sync(
            timeline_path=timeline_path,
            output_dir=output_dir,
        )

    except (
        TTSConfigError,
        TTSEngineError,
        TTSBatchError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print_summary(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())