from __future__ import annotations

import argparse
import asyncio
import json
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from tts_config import (
    TTSConfig,
    TTSConfigError,
)
from tts_engine import (
    EdgeTTSEngine,
    TTSEngineError,
    TTSGenerationResult,
    TTSWordBoundary,
)


class TTSBatchError(RuntimeError):
    """Timeline 기반 TTS 일괄 생성 오류입니다."""


@dataclass(
    frozen=True,
    slots=True,
)
class TimelineScene:
    scene_id: str
    narration: str


@dataclass(
    frozen=True,
    slots=True,
)
class SceneAudioResult:
    scene_id: str
    narration: str

    output_path: Path
    metadata_path: Path

    duration_seconds: float
    file_size_bytes: int

    reused: bool

    word_boundaries: tuple[
        TTSWordBoundary,
        ...,
    ]


@dataclass(
    frozen=True,
    slots=True,
)
class TTSBatchResult:
    episode_id: str
    timeline_path: Path
    output_dir: Path

    generated_count: int
    reused_count: int
    total_count: int

    total_duration: float

    results: tuple[
        SceneAudioResult,
        ...,
    ]


def load_timeline(
    timeline_path: Path,
) -> dict[str, Any]:
    resolved_path = (
        timeline_path.resolve()
    )

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
            timeline_data = json.load(
                file
            )

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

    if not isinstance(
        timeline_data,
        dict,
    ):
        raise TTSBatchError(
            "Timeline 최상위 데이터는 "
            "객체여야 합니다."
        )

    return timeline_data


def read_episode_id(
    *,
    timeline_data: dict[str, Any],
    timeline_path: Path,
) -> str:
    raw_episode_id = (
        timeline_data.get(
            "episodeId"
        )
    )

    if isinstance(
        raw_episode_id,
        str,
    ):
        normalized = (
            raw_episode_id
            .strip()
            .lower()
        )

        if normalized:
            return normalized

    parent_name = (
        timeline_path
        .resolve()
        .parent
        .name
        .strip()
        .lower()
    )

    if parent_name:
        return parent_name

    raise TTSBatchError(
        "Timeline에서 episodeId를 "
        "확인할 수 없습니다."
    )


def load_timeline_scenes(
    timeline_data: dict[str, Any],
) -> list[TimelineScene]:
    raw_scenes = (
        timeline_data.get(
            "scenes"
        )
    )

    if not isinstance(
        raw_scenes,
        list,
    ):
        raise TTSBatchError(
            "Timeline의 scenes 필드가 "
            "배열이 아닙니다."
        )

    if not raw_scenes:
        raise TTSBatchError(
            "Timeline에 scene이 없습니다."
        )

    scenes: list[
        TimelineScene
    ] = []

    seen_scene_ids: set[str] = set()

    for index, raw_scene in enumerate(
        raw_scenes,
        start=1,
    ):
        scene = parse_scene(
            raw_scene=raw_scene,
            scene_number=index,
        )

        if (
            scene.scene_id
            in seen_scene_ids
        ):
            raise TTSBatchError(
                "중복된 scene id가 있습니다: "
                f"{scene.scene_id}"
            )

        seen_scene_ids.add(
            scene.scene_id
        )

        scenes.append(scene)

    return scenes


def parse_scene(
    *,
    raw_scene: Any,
    scene_number: int,
) -> TimelineScene:
    if not isinstance(
        raw_scene,
        dict,
    ):
        raise TTSBatchError(
            f"{scene_number}번째 scene이 "
            "객체 형식이 아닙니다."
        )

    raw_scene_id = raw_scene.get(
        "id"
    )

    if not isinstance(
        raw_scene_id,
        str,
    ):
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

    if not isinstance(
        raw_narration,
        str,
    ):
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


def measure_audio_duration(
    audio_path: Path,
) -> float:
    resolved_path = (
        audio_path.resolve()
    )

    if not resolved_path.exists():
        raise TTSBatchError(
            "오디오 파일을 찾을 수 없습니다:\n"
            f"{resolved_path}"
        )

    if (
        resolved_path
        .stat()
        .st_size
        <= 0
    ):
        raise TTSBatchError(
            "오디오 파일의 크기가 0입니다:\n"
            f"{resolved_path}"
        )

    audio_clip = None

    try:
        try:
            from moviepy import (
                AudioFileClip,
            )

        except ImportError:
            from moviepy.editor import (
                AudioFileClip,
            )

        audio_clip = AudioFileClip(
            str(resolved_path)
        )

        raw_duration = (
            audio_clip.duration
        )

        if raw_duration is None:
            raise TTSBatchError(
                "오디오 길이를 확인할 수 없습니다:\n"
                f"{resolved_path}"
            )

        duration = round(
            float(raw_duration),
            3,
        )

    except TTSBatchError:
        raise

    except Exception as exc:
        raise TTSBatchError(
            "오디오 길이 측정에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc

    finally:
        if audio_clip is not None:
            try:
                audio_clip.close()

            except Exception:
                pass

    if duration <= 0:
        raise TTSBatchError(
            "측정된 오디오 길이가 "
            "0초 이하입니다.\n"
            f"파일: {resolved_path}\n"
            f"길이: {duration}"
        )

    return duration


def build_episode_relative_path(
    *,
    timeline_path: Path,
    target_path: Path,
) -> str:
    episode_dir = (
        timeline_path
        .resolve()
        .parent
    )

    try:
        relative_path = (
            target_path
            .resolve()
            .relative_to(
                episode_dir
            )
        )

    except ValueError:
        relative_path = (
            target_path.resolve()
        )

    return relative_path.as_posix()


def convert_word_boundaries(
    boundaries: tuple[
        TTSWordBoundary,
        ...,
    ],
) -> list[dict[str, object]]:
    return [
        {
            "text": boundary.text,
            "offset": round(
                boundary.offset_seconds,
                3,
            ),
            "duration": round(
                boundary.duration_seconds,
                3,
            ),
            "end": round(
                boundary.end_seconds,
                3,
            ),
        }
        for boundary in boundaries
    ]


def validate_word_boundaries(
    *,
    scene_id: str,
    narration: str,
    boundaries: tuple[
        TTSWordBoundary,
        ...,
    ],
    audio_duration: float,
) -> None:
    if not boundaries:
        raise TTSBatchError(
            f"{scene_id}: 단어별 TTS 타이밍이 "
            "비어 있습니다."
        )

    previous_offset = -1.0

    for index, boundary in enumerate(
        boundaries,
        start=1,
    ):
        if not boundary.text.strip():
            raise TTSBatchError(
                f"{scene_id}: {index}번째 "
                "단어 타이밍의 text가 "
                "비어 있습니다."
            )

        if boundary.offset_seconds < 0:
            raise TTSBatchError(
                f"{scene_id}: {index}번째 "
                "단어 offset이 음수입니다."
            )

        if boundary.duration_seconds < 0:
            raise TTSBatchError(
                f"{scene_id}: {index}번째 "
                "단어 duration이 음수입니다."
            )

        if (
            boundary.offset_seconds
            < previous_offset
        ):
            raise TTSBatchError(
                f"{scene_id}: 단어 타이밍 "
                "순서가 올바르지 않습니다."
            )

        previous_offset = (
            boundary.offset_seconds
        )

    last_boundary = boundaries[-1]

    duration_tolerance = 1.0

    if (
        last_boundary.end_seconds
        > audio_duration
        + duration_tolerance
    ):
        raise TTSBatchError(
            f"{scene_id}: 마지막 단어 종료 시각이 "
            "오디오 길이를 초과합니다.\n"
            f"마지막 단어: "
            f"{last_boundary.end_seconds:.3f}초\n"
            f"오디오: {audio_duration:.3f}초"
        )

    normalized_narration = (
        narration
        .replace(" ", "")
    )

    normalized_boundary_text = (
        "".join(
            boundary.text
            for boundary in boundaries
        )
        .replace(" ", "")
    )

    if not normalized_boundary_text:
        raise TTSBatchError(
            f"{scene_id}: 타이밍 텍스트를 "
            "확인할 수 없습니다."
        )

    # 문장부호 처리 차이 때문에 완전 일치 검사는 하지 않고,
    # 타이밍 데이터가 실제 대사와 전혀 다른 경우만 차단합니다.
    matching_character_count = sum(
        1
        for character
        in normalized_boundary_text
        if character
        in normalized_narration
    )

    matching_ratio = (
        matching_character_count
        / max(
            1,
            len(
                normalized_boundary_text
            ),
        )
    )

    if matching_ratio < 0.5:
        raise TTSBatchError(
            f"{scene_id}: TTS 타이밍 텍스트가 "
            "narration과 일치하지 않습니다."
        )


def synchronize_timeline(
    *,
    timeline_data: dict[str, Any],
    timeline_path: Path,
    audio_results: list[
        SceneAudioResult
    ],
    scene_gap_ms: int,
) -> float:
    raw_scenes = timeline_data.get(
        "scenes"
    )

    if not isinstance(
        raw_scenes,
        list,
    ):
        raise TTSBatchError(
            "Timeline의 scenes 필드가 "
            "배열이 아닙니다."
        )

    if (
        len(raw_scenes)
        != len(audio_results)
    ):
        raise TTSBatchError(
            "Timeline 장면 수와 오디오 결과 수가 "
            "다릅니다.\n"
            f"Timeline: {len(raw_scenes)}\n"
            f"Audio: {len(audio_results)}"
        )

    gap_seconds = round(
        scene_gap_ms / 1000,
        3,
    )

    current_start = 0.0

    for index, (
        raw_scene,
        audio_result,
    ) in enumerate(
        zip(
            raw_scenes,
            audio_results,
            strict=True,
        )
    ):
        if not isinstance(
            raw_scene,
            dict,
        ):
            raise TTSBatchError(
                f"{index + 1}번째 scene이 "
                "객체 형식이 아닙니다."
            )

        raw_scene_id = raw_scene.get(
            "id"
        )

        if (
            raw_scene_id
            != audio_result.scene_id
        ):
            raise TTSBatchError(
                "Timeline 장면 순서와 "
                "오디오 순서가 일치하지 않습니다.\n"
                f"Timeline scene: {raw_scene_id}\n"
                f"Audio scene: "
                f"{audio_result.scene_id}"
            )

        is_last_scene = (
            index
            == len(audio_results) - 1
        )

        scene_duration = (
            audio_result.duration_seconds
            if is_last_scene
            else round(
                audio_result.duration_seconds
                + gap_seconds,
                3,
            )
        )

        raw_scene["start"] = round(
            current_start,
            3,
        )

        raw_scene["duration"] = (
            scene_duration
        )

        raw_scene["audioDuration"] = (
            audio_result.duration_seconds
        )

        episode_id = timeline_path.parent.name

        audio_relative_path = (
            build_episode_relative_path(
                timeline_path=timeline_path,
                target_path=(
                    audio_result.output_path
                ),
            )
        )

        timing_relative_path = (
            build_episode_relative_path(
                timeline_path=timeline_path,
                target_path=(
                    audio_result.metadata_path
                ),
            )
        )

        raw_scene["audio"] = (
            f"{episode_id}/"
            f"{audio_relative_path}"
        )

        raw_scene["timing"] = (
            f"{episode_id}/"
            f"{timing_relative_path}"
        )

        raw_scene["wordTimings"] = (
            convert_word_boundaries(
                audio_result.word_boundaries
            )
        )

        raw_scene["wordCount"] = len(
            audio_result.word_boundaries
        )

        current_start = round(
            current_start
            + scene_duration,
            3,
        )

    total_duration = round(
        current_start,
        3,
    )

    timeline_data["totalDuration"] = (
        total_duration
    )

    timeline_data["tts"] = {
        "provider": "edge",
        "sceneGapMs": scene_gap_ms,
        "audioDirectory": (
            f"{timeline_path.parent.name}/audio"
        ),
        "synchronized": True,
        "wordTiming": True,
        "timingVersion": "1.0",
    }

    return total_duration


def save_timeline(
    *,
    timeline_data: dict[str, Any],
    timeline_path: Path,
) -> None:
    resolved_path = (
        timeline_path.resolve()
    )

    backup_path = (
        resolved_path.with_suffix(
            ".json.bak"
        )
    )

    temporary_path = (
        resolved_path.with_suffix(
            ".json.tmp"
        )
    )

    try:
        shutil.copy2(
            resolved_path,
            backup_path,
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
        ) as file:
            json.dump(
                timeline_data,
                file,
                ensure_ascii=False,
                indent=2,
            )

            file.write("\n")

        temporary_path.replace(
            resolved_path
        )

    except OSError as exc:
        if temporary_path.exists():
            temporary_path.unlink()

        raise TTSBatchError(
            "Timeline 저장에 실패했습니다.\n"
            f"파일: {resolved_path}\n"
            f"원인: {exc}"
        ) from exc


class TimelineTTSBatchGenerator:
    """
    Timeline의 narration을 장면별 음성으로 만들고,
    오디오 길이와 단어별 발화 시각을 Timeline에
    동기화합니다.
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
        sync_timeline: bool = True,
    ) -> TTSBatchResult:
        resolved_timeline_path = (
            timeline_path.resolve()
        )

        timeline_data = load_timeline(
            resolved_timeline_path
        )

        episode_id = read_episode_id(
            timeline_data=timeline_data,
            timeline_path=(
                resolved_timeline_path
            ),
        )

        scenes = load_timeline_scenes(
            timeline_data
        )

        resolved_output_dir = (
            output_dir.resolve()
            if output_dir is not None
            else (
                resolved_timeline_path
                .parent
                / "audio"
            )
        )

        resolved_output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        audio_results: list[
            SceneAudioResult
        ] = []

        generated_count = 0
        reused_count = 0

        print("=" * 66)
        print(
            " YouTube Content Factory "
            "TTS + Word Timing Sync"
        )
        print("=" * 66)
        print(
            f"{'episode':>18}: "
            f"{episode_id}"
        )
        print(
            f"{'timeline':>18}: "
            f"{resolved_timeline_path}"
        )
        print(
            f"{'output':>18}: "
            f"{resolved_output_dir}"
        )
        print(
            f"{'scene_count':>18}: "
            f"{len(scenes)}"
        )
        print("-" * 66)

        for index, scene in enumerate(
            scenes,
            start=1,
        ):
            expected_audio_path = (
                self.engine
                .config
                .build_scene_path(
                    output_dir=(
                        resolved_output_dir
                    ),
                    scene_id=(
                        scene.scene_id
                    ),
                )
            )

            expected_metadata_path = (
                resolved_output_dir
                / (
                    f"{scene.scene_id}"
                    ".timing.json"
                )
            )

            cache_existed_before = (
                expected_audio_path.exists()
                and expected_audio_path
                .stat()
                .st_size
                > 0
                and expected_metadata_path
                .exists()
                and expected_metadata_path
                .stat()
                .st_size
                > 0
                and not self.engine
                .config
                .overwrite
            )

            print(
                f"[{index}/{len(scenes)}] "
                f"{scene.scene_id}"
            )

            print(
                f"       대사: "
                f"{scene.narration}"
            )

            generation_result: (
                TTSGenerationResult
            ) = await self.engine.generate(
                scene_id=scene.scene_id,
                text=scene.narration,
                output_dir=(
                    resolved_output_dir
                ),
            )

            duration_seconds = (
                measure_audio_duration(
                    generation_result.output_path
                )
            )

            validate_word_boundaries(
                scene_id=scene.scene_id,
                narration=scene.narration,
                boundaries=(
                    generation_result
                    .word_boundaries
                ),
                audio_duration=(
                    duration_seconds
                ),
            )

            audio_result = SceneAudioResult(
                scene_id=scene.scene_id,
                narration=scene.narration,
                output_path=(
                    generation_result
                    .output_path
                ),
                metadata_path=(
                    generation_result
                    .metadata_path
                ),
                duration_seconds=(
                    duration_seconds
                ),
                file_size_bytes=(
                    generation_result
                    .file_size_bytes
                ),
                reused=(
                    cache_existed_before
                ),
                word_boundaries=(
                    generation_result
                    .word_boundaries
                ),
            )

            audio_results.append(
                audio_result
            )

            if cache_existed_before:
                reused_count += 1

            else:
                generated_count += 1

            print(
                f"       음성: "
                f"{audio_result.output_path.name}"
            )
            print(
                f"       타이밍: "
                f"{audio_result.metadata_path.name}"
            )
            print(
                f"       길이: "
                f"{audio_result.duration_seconds:.3f}초"
            )
            print(
                f"       단어: "
                f"{len(audio_result.word_boundaries)}개"
            )
            print(
                f"       크기: "
                f"{audio_result.file_size_bytes:,} bytes"
            )

        total_duration = round(
            sum(
                result.duration_seconds
                for result
                in audio_results
            ),
            3,
        )

        if sync_timeline:
            total_duration = (
                synchronize_timeline(
                    timeline_data=timeline_data,
                    timeline_path=(
                        resolved_timeline_path
                    ),
                    audio_results=(
                        audio_results
                    ),
                    scene_gap_ms=(
                        self.engine
                        .config
                        .scene_gap_ms
                    ),
                )
            )

            save_timeline(
                timeline_data=timeline_data,
                timeline_path=(
                    resolved_timeline_path
                ),
            )

        return TTSBatchResult(
            episode_id=episode_id,
            timeline_path=(
                resolved_timeline_path
            ),
            output_dir=(
                resolved_output_dir
            ),
            generated_count=(
                generated_count
            ),
            reused_count=(
                reused_count
            ),
            total_count=len(
                audio_results
            ),
            total_duration=(
                total_duration
            ),
            results=tuple(
                audio_results
            ),
        )

    def generate_sync(
        self,
        *,
        timeline_path: Path,
        output_dir: Path | None = None,
        sync_timeline: bool = True,
    ) -> TTSBatchResult:
        try:
            asyncio.get_running_loop()

        except RuntimeError:
            return asyncio.run(
                self.generate(
                    timeline_path=(
                        timeline_path
                    ),
                    output_dir=(
                        output_dir
                    ),
                    sync_timeline=(
                        sync_timeline
                    ),
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
        return Path(
            timeline_argument
        )

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

    return Path(
        output_argument
    )


def build_argument_parser(
) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Timeline narration으로 TTS와 "
            "단어 발화 타이밍을 생성하고 "
            "Timeline에 동기화합니다."
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
            "생략하면 에피소드의 audio "
            "폴더를 사용합니다."
        ),
    )

    parser.add_argument(
        "--overwrite",
        action="store_true",
        help=(
            "기존 MP3와 타이밍 파일이 있어도 "
            "새로 생성합니다."
        ),
    )

    parser.add_argument(
        "--no-sync",
        action="store_true",
        help=(
            "음성과 타이밍만 생성하고 "
            "timeline.json은 수정하지 않습니다."
        ),
    )

    return parser


def print_summary(
    result: TTSBatchResult,
) -> None:
    total_word_count = sum(
        len(
            scene_result
            .word_boundaries
        )
        for scene_result
        in result.results
    )

    print("-" * 66)
    print(
        "[완료] TTS, Duration, "
        "Word Timing 동기화"
    )
    print(
        f"{'전체 장면':>18}: "
        f"{result.total_count}"
    )
    print(
        f"{'새로 생성':>18}: "
        f"{result.generated_count}"
    )
    print(
        f"{'기존 사용':>18}: "
        f"{result.reused_count}"
    )
    print(
        f"{'전체 단어':>18}: "
        f"{total_word_count}"
    )
    print(
        f"{'전체 길이':>18}: "
        f"{result.total_duration:.3f}초"
    )
    print(
        f"{'저장 폴더':>18}: "
        f"{result.output_dir}"
    )
    print(
        f"{'Timeline':>18}: "
        f"{result.timeline_path}"
    )


def main() -> int:
    parser = build_argument_parser()

    arguments = parser.parse_args()

    timeline_path = (
        resolve_timeline_path(
            episode=arguments.episode,
            timeline_argument=(
                arguments.timeline
            ),
        )
    )

    output_dir = resolve_output_dir(
        arguments.output_dir
    )

    try:
        base_config = (
            TTSConfig.from_environment()
        )

        config = TTSConfig(
            provider=(
                base_config.provider
            ),
            language=(
                base_config.language
            ),
            voice=(
                base_config.voice
            ),
            rate=(
                base_config.rate
            ),
            volume=(
                base_config.volume
            ),
            pitch=(
                base_config.pitch
            ),
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
            timeline_path=(
                timeline_path
            ),
            output_dir=(
                output_dir
            ),
            sync_timeline=(
                not arguments.no_sync
            ),
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
    raise SystemExit(
        main()
    )