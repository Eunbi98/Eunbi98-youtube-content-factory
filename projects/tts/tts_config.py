from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Final


DEFAULT_PROVIDER: Final[str] = "edge"
DEFAULT_LANGUAGE: Final[str] = "ko-KR"
DEFAULT_VOICE: Final[str] = "ko-KR-SunHiNeural"
DEFAULT_RATE: Final[str] = "+0%"
DEFAULT_VOLUME: Final[str] = "+0%"
DEFAULT_PITCH: Final[str] = "+0Hz"
DEFAULT_AUDIO_FORMAT: Final[str] = "mp3"
DEFAULT_SCENE_GAP_MS: Final[int] = 150


class TTSConfigError(ValueError):
    """TTS 설정값이 올바르지 않을 때 발생하는 예외입니다."""


@dataclass(frozen=True, slots=True)
class TTSConfig:
    """
    YouTube Content Factory TTS 엔진 공통 설정입니다.

    환경변수가 설정되어 있으면 환경변수를 우선 사용하고,
    설정되지 않은 값은 한국어 Shorts 기본값을 사용합니다.
    """

    provider: str = DEFAULT_PROVIDER
    language: str = DEFAULT_LANGUAGE
    voice: str = DEFAULT_VOICE
    rate: str = DEFAULT_RATE
    volume: str = DEFAULT_VOLUME
    pitch: str = DEFAULT_PITCH
    audio_format: str = DEFAULT_AUDIO_FORMAT
    scene_gap_ms: int = DEFAULT_SCENE_GAP_MS
    overwrite: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "provider",
            self.provider.strip().lower(),
        )
        object.__setattr__(
            self,
            "language",
            self.language.strip(),
        )
        object.__setattr__(
            self,
            "voice",
            self.voice.strip(),
        )
        object.__setattr__(
            self,
            "rate",
            self.rate.strip(),
        )
        object.__setattr__(
            self,
            "volume",
            self.volume.strip(),
        )
        object.__setattr__(
            self,
            "pitch",
            self.pitch.strip(),
        )
        object.__setattr__(
            self,
            "audio_format",
            self.audio_format.strip().lower().lstrip("."),
        )

        self.validate()

    def validate(self) -> None:
        if not self.provider:
            raise TTSConfigError(
                "TTS provider가 비어 있습니다."
            )

        if self.provider not in {"edge"}:
            raise TTSConfigError(
                "지원하지 않는 TTS provider입니다: "
                f"{self.provider}"
            )

        if not self.language:
            raise TTSConfigError(
                "TTS language가 비어 있습니다."
            )

        if not self.voice:
            raise TTSConfigError(
                "TTS voice가 비어 있습니다."
            )

        self._validate_percentage(
            name="rate",
            value=self.rate,
        )
        self._validate_percentage(
            name="volume",
            value=self.volume,
        )
        self._validate_pitch(self.pitch)

        if self.audio_format not in {"mp3"}:
            raise TTSConfigError(
                "지원하지 않는 오디오 형식입니다: "
                f"{self.audio_format}"
            )

        if self.scene_gap_ms < 0:
            raise TTSConfigError(
                "scene_gap_ms는 0 이상이어야 합니다."
            )

        if self.scene_gap_ms > 5000:
            raise TTSConfigError(
                "scene_gap_ms는 5000ms 이하여야 합니다."
            )

    @staticmethod
    def _validate_percentage(
        *,
        name: str,
        value: str,
    ) -> None:
        if len(value) < 3:
            raise TTSConfigError(
                f"{name} 형식이 올바르지 않습니다: {value}"
            )

        if value[0] not in {"+", "-"}:
            raise TTSConfigError(
                f"{name}는 + 또는 -로 시작해야 합니다: "
                f"{value}"
            )

        if not value.endswith("%"):
            raise TTSConfigError(
                f"{name}는 %로 끝나야 합니다: {value}"
            )

        number_text = value[1:-1]

        if not number_text.isdigit():
            raise TTSConfigError(
                f"{name} 숫자값이 올바르지 않습니다: "
                f"{value}"
            )

        number = int(number_text)

        if number > 100:
            raise TTSConfigError(
                f"{name} 절댓값은 100 이하여야 합니다: "
                f"{value}"
            )

    @staticmethod
    def _validate_pitch(value: str) -> None:
        if len(value) < 4:
            raise TTSConfigError(
                f"pitch 형식이 올바르지 않습니다: {value}"
            )

        if value[0] not in {"+", "-"}:
            raise TTSConfigError(
                "pitch는 + 또는 -로 시작해야 합니다: "
                f"{value}"
            )

        if not value.endswith("Hz"):
            raise TTSConfigError(
                f"pitch는 Hz로 끝나야 합니다: {value}"
            )

        number_text = value[1:-2]

        if not number_text.isdigit():
            raise TTSConfigError(
                f"pitch 숫자값이 올바르지 않습니다: "
                f"{value}"
            )

        number = int(number_text)

        if number > 100:
            raise TTSConfigError(
                "pitch 절댓값은 100Hz 이하여야 합니다: "
                f"{value}"
            )

    @classmethod
    def from_environment(cls) -> "TTSConfig":
        """
        환경변수에서 TTS 설정을 생성합니다.

        지원 환경변수:
        - YCF_TTS_PROVIDER
        - YCF_TTS_LANGUAGE
        - YCF_TTS_VOICE
        - YCF_TTS_RATE
        - YCF_TTS_VOLUME
        - YCF_TTS_PITCH
        - YCF_TTS_AUDIO_FORMAT
        - YCF_TTS_SCENE_GAP_MS
        - YCF_TTS_OVERWRITE
        """

        return cls(
            provider=os.getenv(
                "YCF_TTS_PROVIDER",
                DEFAULT_PROVIDER,
            ),
            language=os.getenv(
                "YCF_TTS_LANGUAGE",
                DEFAULT_LANGUAGE,
            ),
            voice=os.getenv(
                "YCF_TTS_VOICE",
                DEFAULT_VOICE,
            ),
            rate=os.getenv(
                "YCF_TTS_RATE",
                DEFAULT_RATE,
            ),
            volume=os.getenv(
                "YCF_TTS_VOLUME",
                DEFAULT_VOLUME,
            ),
            pitch=os.getenv(
                "YCF_TTS_PITCH",
                DEFAULT_PITCH,
            ),
            audio_format=os.getenv(
                "YCF_TTS_AUDIO_FORMAT",
                DEFAULT_AUDIO_FORMAT,
            ),
            scene_gap_ms=_read_int_environment(
                name="YCF_TTS_SCENE_GAP_MS",
                default=DEFAULT_SCENE_GAP_MS,
            ),
            overwrite=_read_bool_environment(
                name="YCF_TTS_OVERWRITE",
                default=False,
            ),
        )

    def build_scene_filename(
        self,
        scene_id: str,
    ) -> str:
        normalized_scene_id = scene_id.strip()

        if not normalized_scene_id:
            raise TTSConfigError(
                "scene_id가 비어 있습니다."
            )

        return (
            f"{normalized_scene_id}."
            f"{self.audio_format}"
        )

    def build_scene_path(
        self,
        output_dir: Path,
        scene_id: str,
    ) -> Path:
        return (
            output_dir
            / self.build_scene_filename(scene_id)
        )

    def to_dict(self) -> dict[str, object]:
        return {
            "provider": self.provider,
            "language": self.language,
            "voice": self.voice,
            "rate": self.rate,
            "volume": self.volume,
            "pitch": self.pitch,
            "audio_format": self.audio_format,
            "scene_gap_ms": self.scene_gap_ms,
            "overwrite": self.overwrite,
        }


def _read_int_environment(
    *,
    name: str,
    default: int,
) -> int:
    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    try:
        return int(raw_value.strip())
    except ValueError as exc:
        raise TTSConfigError(
            f"{name} 환경변수는 정수여야 합니다: "
            f"{raw_value}"
        ) from exc


def _read_bool_environment(
    *,
    name: str,
    default: bool,
) -> bool:
    raw_value = os.getenv(name)

    if raw_value is None or not raw_value.strip():
        return default

    normalized = raw_value.strip().lower()

    if normalized in {
        "1",
        "true",
        "yes",
        "y",
        "on",
    }:
        return True

    if normalized in {
        "0",
        "false",
        "no",
        "n",
        "off",
    }:
        return False

    raise TTSConfigError(
        f"{name} 환경변수의 불리언 값이 "
        f"올바르지 않습니다: {raw_value}"
    )


def main() -> int:
    try:
        config = TTSConfig.from_environment()
    except TTSConfigError as exc:
        print(f"[실패] TTS 설정 오류: {exc}")
        return 1

    print("=" * 58)
    print(" YouTube Content Factory Release 6.3")
    print(" TTS Configuration")
    print("=" * 58)

    for key, value in config.to_dict().items():
        print(f"{key:>16}: {value}")

    sample_path = config.build_scene_path(
        output_dir=Path(
            "projects/episodes/ep008/audio"
        ),
        scene_id="scene_001",
    )

    print("-" * 58)
    print(f"{'sample_path':>16}: {sample_path}")
    print("[성공] TTS 설정 검증 완료")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())