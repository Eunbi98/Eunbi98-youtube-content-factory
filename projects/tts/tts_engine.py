from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Final

import edge_tts

from tts_config import TTSConfig, TTSConfigError


DEFAULT_TEST_TEXT: Final[str] = (
    "사람이 절대 들어갈 수 없는 장소가 "
    "실제로 존재한다는 사실, 알고 계셨나요?"
)


class TTSEngineError(RuntimeError):
    """TTS 음성 생성 과정에서 발생하는 예외입니다."""


@dataclass(frozen=True, slots=True)
class TTSGenerationResult:
    scene_id: str
    text: str
    output_path: Path
    voice: str
    rate: str
    volume: str
    pitch: str
    file_size_bytes: int

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "text": self.text,
            "output_path": str(self.output_path),
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch,
            "file_size_bytes": self.file_size_bytes,
        }


class EdgeTTSEngine:
    """
    Microsoft Edge TTS를 사용하는 음성 생성 엔진입니다.

    기존 Timeline이나 Factory Runner는 수정하지 않고,
    전달받은 문장을 장면별 MP3 파일로 저장합니다.
    """

    def __init__(
        self,
        config: TTSConfig | None = None,
    ) -> None:
        self.config = (
            config
            if config is not None
            else TTSConfig.from_environment()
        )

        if self.config.provider != "edge":
            raise TTSEngineError(
                "EdgeTTSEngine은 provider가 "
                "'edge'일 때만 사용할 수 있습니다."
            )

    async def generate(
        self,
        *,
        scene_id: str,
        text: str,
        output_dir: Path,
    ) -> TTSGenerationResult:
        normalized_scene_id = self._normalize_scene_id(
            scene_id
        )
        normalized_text = self._normalize_text(text)

        output_dir = output_dir.resolve()
        output_dir.mkdir(
            parents=True,
            exist_ok=True,
        )

        output_path = self.config.build_scene_path(
            output_dir=output_dir,
            scene_id=normalized_scene_id,
        )

        if output_path.exists():
            if not self.config.overwrite:
                file_size = output_path.stat().st_size

                if file_size > 0:
                    print(
                        "[건너뜀] 기존 TTS 파일 사용: "
                        f"{output_path}"
                    )

                    return TTSGenerationResult(
                        scene_id=normalized_scene_id,
                        text=normalized_text,
                        output_path=output_path,
                        voice=self.config.voice,
                        rate=self.config.rate,
                        volume=self.config.volume,
                        pitch=self.config.pitch,
                        file_size_bytes=file_size,
                    )

            output_path.unlink()

        temporary_path = output_path.with_suffix(
            f"{output_path.suffix}.part"
        )

        if temporary_path.exists():
            temporary_path.unlink()

        try:
            communicate = edge_tts.Communicate(
                text=normalized_text,
                voice=self.config.voice,
                rate=self.config.rate,
                volume=self.config.volume,
                pitch=self.config.pitch,
            )

            await communicate.save(
                str(temporary_path)
            )

            self._validate_generated_file(
                temporary_path
            )

            temporary_path.replace(output_path)

        except Exception as exc:
            if temporary_path.exists():
                temporary_path.unlink()

            raise TTSEngineError(
                "TTS 음성 생성에 실패했습니다.\n"
                f"scene_id: {normalized_scene_id}\n"
                f"voice: {self.config.voice}\n"
                f"output: {output_path}\n"
                f"원인: {exc}"
            ) from exc

        file_size = output_path.stat().st_size

        return TTSGenerationResult(
            scene_id=normalized_scene_id,
            text=normalized_text,
            output_path=output_path,
            voice=self.config.voice,
            rate=self.config.rate,
            volume=self.config.volume,
            pitch=self.config.pitch,
            file_size_bytes=file_size,
        )

    def generate_sync(
        self,
        *,
        scene_id: str,
        text: str,
        output_dir: Path,
    ) -> TTSGenerationResult:
        """
        일반 Python 코드에서 사용할 수 있는 동기 실행 함수입니다.
        """

        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.generate(
                    scene_id=scene_id,
                    text=text,
                    output_dir=output_dir,
                )
            )

        raise TTSEngineError(
            "이미 실행 중인 asyncio 이벤트 루프가 있습니다. "
            "비동기 환경에서는 await engine.generate(...)를 "
            "사용하세요."
        )

    @staticmethod
    def _normalize_scene_id(
        scene_id: str,
    ) -> str:
        normalized = scene_id.strip()

        if not normalized:
            raise TTSEngineError(
                "scene_id가 비어 있습니다."
            )

        invalid_characters = {
            "<",
            ">",
            ":",
            '"',
            "/",
            "\\",
            "|",
            "?",
            "*",
        }

        found_invalid = sorted(
            character
            for character in invalid_characters
            if character in normalized
        )

        if found_invalid:
            raise TTSEngineError(
                "scene_id에 파일명으로 사용할 수 없는 "
                "문자가 포함되어 있습니다: "
                + ", ".join(found_invalid)
            )

        return normalized

    @staticmethod
    def _normalize_text(
        text: str,
    ) -> str:
        normalized = " ".join(
            text.replace("\r", " ")
            .replace("\n", " ")
            .split()
        )

        if not normalized:
            raise TTSEngineError(
                "TTS로 변환할 문장이 비어 있습니다."
            )

        if len(normalized) > 5000:
            raise TTSEngineError(
                "한 장면의 TTS 문장은 "
                "5000자를 초과할 수 없습니다."
            )

        return normalized

    @staticmethod
    def _validate_generated_file(
        output_path: Path,
    ) -> None:
        if not output_path.exists():
            raise TTSEngineError(
                "TTS 출력 파일이 생성되지 않았습니다: "
                f"{output_path}"
            )

        file_size = output_path.stat().st_size

        if file_size <= 0:
            raise TTSEngineError(
                "생성된 TTS 파일의 크기가 0입니다: "
                f"{output_path}"
            )


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "YouTube Content Factory "
            "Release 6.3 Edge TTS 테스트"
        )
    )

    parser.add_argument(
        "--episode",
        default="ep008",
        help="에피소드 ID입니다. 기본값: ep008",
    )

    parser.add_argument(
        "--scene-id",
        default="scene_001",
        help="장면 ID입니다. 기본값: scene_001",
    )

    parser.add_argument(
        "--text",
        default=DEFAULT_TEST_TEXT,
        help="음성으로 생성할 문장입니다.",
    )

    parser.add_argument(
        "--output-dir",
        default=None,
        help=(
            "TTS 저장 폴더입니다. 생략하면 "
            "projects/episodes/{episode}/audio를 사용합니다."
        ),
    )

    return parser


def resolve_output_dir(
    *,
    episode: str,
    output_dir_argument: str | None,
) -> Path:
    if output_dir_argument:
        return Path(output_dir_argument)

    project_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    return (
        project_root
        / "projects"
        / "episodes"
        / episode
        / "audio"
    )


def print_result(
    result: TTSGenerationResult,
) -> None:
    print("=" * 58)
    print(" YouTube Content Factory Release 6.3")
    print(" Edge TTS Generation")
    print("=" * 58)
    print(f"{'scene_id':>16}: {result.scene_id}")
    print(f"{'voice':>16}: {result.voice}")
    print(f"{'rate':>16}: {result.rate}")
    print(f"{'volume':>16}: {result.volume}")
    print(f"{'pitch':>16}: {result.pitch}")
    print(
        f"{'file_size':>16}: "
        f"{result.file_size_bytes:,} bytes"
    )
    print(f"{'output':>16}: {result.output_path}")
    print("-" * 58)
    print(f"{'text':>16}: {result.text}")
    print("[성공] TTS 음성 파일 생성 완료")


def main() -> int:
    parser = build_argument_parser()
    arguments = parser.parse_args()

    try:
        config = TTSConfig.from_environment()

        engine = EdgeTTSEngine(
            config=config
        )

        output_dir = resolve_output_dir(
            episode=arguments.episode,
            output_dir_argument=arguments.output_dir,
        )

        result = engine.generate_sync(
            scene_id=arguments.scene_id,
            text=arguments.text,
            output_dir=output_dir,
        )

    except (
        TTSConfigError,
        TTSEngineError,
    ) as exc:
        print(
            f"[실패] {exc}",
            file=sys.stderr,
        )
        return 1

    print_result(result)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())