from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path


class AudioDurationError(RuntimeError):
    """오디오 재생 시간 측정 과정에서 발생하는 오류입니다."""


@dataclass(frozen=True, slots=True)
class AudioDurationResult:
    audio_path: Path
    duration_seconds: float
    file_size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "audio_path": str(self.audio_path),
            "duration_seconds": self.duration_seconds,
            "file_size_bytes": self.file_size_bytes,
        }


def measure_audio_duration(
    audio_path: Path,
    *,
    precision: int = 3,
) -> AudioDurationResult:
    """
    MP3 등 오디오 파일의 실제 재생 시간을 측정합니다.

    MoviePy 2.x와 1.x를 모두 지원합니다.
    """

    resolved_path = audio_path.resolve()

    if not resolved_path.exists():
        raise AudioDurationError(
            "오디오 파일을 찾을 수 없습니다:\n"
            f"{resolved_path}"
        )

    if not resolved_path.is_file():
        raise AudioDurationError(
            "오디오 경로가 파일이 아닙니다:\n"
            f"{resolved_path}"
        )

    file_size = resolved_path.stat().st_size

    if file_size <= 0:
        raise AudioDurationError(
            "오디오 파일의 크기가 0입니다:\n"
            f"{resolved_path}"
        )

    if precision < 0 or precision > 6:
        raise AudioDurationError(
            "precision은 0 이상 6 이하이어야 합니다."
        )

    audio_clip = None

    try:
        try:
            from moviepy import AudioFileClip
        except ImportError:
            from moviepy.editor import AudioFileClip

        audio_clip = AudioFileClip(
            str(resolved_path)
        )

        raw_duration = audio_clip.duration

        if raw_duration is None:
            raise AudioDurationError(
                "오디오 재생 시간을 확인할 수 없습니다:\n"
                f"{resolved_path}"
            )

        duration = round(
            float(raw_duration),
            precision,
        )

    except AudioDurationError:
        raise

    except Exception as exc:
        raise AudioDurationError(
            "오디오 재생 시간 측정에 실패했습니다.\n"
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
        raise AudioDurationError(
            "측정된 오디오 길이가 0초 이하입니다.\n"
            f"파일: {resolved_path}\n"
            f"길이: {duration}"
        )

    return AudioDurationResult(
        audio_path=resolved_path,
        duration_seconds=duration,
        file_size_bytes=file_size,
    )


def measure_audio_directory(
    audio_dir: Path,
    *,
    extension: str = ".mp3",
    precision: int = 3,
) -> tuple[AudioDurationResult, ...]:
    """
    폴더 내 오디오 파일들의 재생 시간을 파일명순으로 측정합니다.
    """

    resolved_dir = audio_dir.resolve()

    if not resolved_dir.exists():
        raise AudioDurationError(
            "오디오 폴더를 찾을 수 없습니다:\n"
            f"{resolved_dir}"
        )

    if not resolved_dir.is_dir():
        raise AudioDurationError(
            "오디오 경로가 폴더가 아닙니다:\n"
            f"{resolved_dir}"
        )

    normalized_extension = extension.strip().lower()

    if not normalized_extension:
        raise AudioDurationError(
            "오디오 확장자가 비어 있습니다."
        )

    if not normalized_extension.startswith("."):
        normalized_extension = (
            f".{normalized_extension}"
        )

    audio_files = sorted(
        (
            path
            for path in resolved_dir.iterdir()
            if path.is_file()
            and path.suffix.lower()
            == normalized_extension
        ),
        key=lambda path: path.name.lower(),
    )

    if not audio_files:
        raise AudioDurationError(
            "측정할 오디오 파일이 없습니다.\n"
            f"폴더: {resolved_dir}\n"
            f"확장자: {normalized_extension}"
        )

    results = tuple(
        measure_audio_duration(
            audio_path,
            precision=precision,
        )
        for audio_path in audio_files
    )

    return results


def resolve_project_root() -> Path:
    return (
        Path(__file__)
        .resolve()
        .parents[2]
    )


def resolve_audio_path(
    *,
    episode: str,
    scene_id: str,
    audio_argument: str | None,
) -> Path:
    if audio_argument:
        return Path(audio_argument)

    return (
        resolve_project_root()
        / "projects"
        / "episodes"
        / episode
        / "audio"
        / f"{scene_id}.mp3"
    )


def resolve_audio_dir(
    *,
    episode: str,
    audio_dir_argument: str | None,
) -> Path:
    if audio_dir_argument:
        return Path(audio_dir_argument)

    return (
        resolve_project_root()
        / "projects"
        / "episodes"
        / episode
        / "audio"
    )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "YouTube Content Factory Release 6.3 "
            "오디오 재생 시간 측정"
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
        "--scene-id",
        default="scene_001",
        help=(
            "측정할 장면 ID입니다. "
            "기본값: scene_001"
        ),
    )

    parser.add_argument(
        "--audio",
        default=None,
        help=(
            "측정할 오디오 파일 경로입니다. "
            "생략하면 episode와 scene-id를 "
            "기준으로 경로를 생성합니다."
        ),
    )

    parser.add_argument(
        "--audio-dir",
        default=None,
        help=(
            "폴더 내 모든 MP3를 측정할 때 "
            "사용할 오디오 폴더 경로입니다."
        ),
    )

    parser.add_argument(
        "--all",
        action="store_true",
        help=(
            "에피소드 audio 폴더의 "
            "모든 MP3 파일을 측정합니다."
        ),
    )

    parser.add_argument(
        "--precision",
        type=int,
        default=3,
        help=(
            "초 단위 소수점 자릿수입니다. "
            "기본값: 3"
        ),
    )

    return parser


def print_single_result(
    result: AudioDurationResult,
) -> None:
    print("=" * 62)
    print(
        " YouTube Content Factory "
        "Release 6.3"
    )
    print(" Audio Duration Measurement")
    print("=" * 62)
    print(
        f"{'file':>16}: "
        f"{result.audio_path.name}"
    )
    print(
        f"{'duration':>16}: "
        f"{result.duration_seconds:.3f}초"
    )
    print(
        f"{'file_size':>16}: "
        f"{result.file_size_bytes:,} bytes"
    )
    print(
        f"{'path':>16}: "
        f"{result.audio_path}"
    )
    print("-" * 62)
    print("[성공] 오디오 재생 시간 측정 완료")


def print_directory_results(
    results: tuple[AudioDurationResult, ...],
) -> None:
    total_duration = round(
        sum(
            result.duration_seconds
            for result in results
        ),
        3,
    )

    print("=" * 62)
    print(
        " YouTube Content Factory "
        "Release 6.3"
    )
    print(" Audio Directory Measurement")
    print("=" * 62)

    for index, result in enumerate(
        results,
        start=1,
    ):
        print(
            f"[{index}/{len(results)}] "
            f"{result.audio_path.name}"
        )
        print(
            f"       길이: "
            f"{result.duration_seconds:.3f}초"
        )
        print(
            f"       크기: "
            f"{result.file_size_bytes:,} bytes"
        )

    print("-" * 62)
    print(
        f"{'파일 수':>16}: "
        f"{len(results)}"
    )
    print(
        f"{'전체 길이':>16}: "
        f"{total_duration:.3f}초"
    )
    print("[성공] 전체 오디오 길이 측정 완료")


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        if arguments.all:
            audio_dir = resolve_audio_dir(
                episode=arguments.episode,
                audio_dir_argument=(
                    arguments.audio_dir
                ),
            )

            results = measure_audio_directory(
                audio_dir,
                precision=arguments.precision,
            )

            print_directory_results(results)

        else:
            audio_path = resolve_audio_path(
                episode=arguments.episode,
                scene_id=arguments.scene_id,
                audio_argument=arguments.audio,
            )

            result = measure_audio_duration(
                audio_path,
                precision=arguments.precision,
            )

            print_single_result(result)

    except AudioDurationError as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())