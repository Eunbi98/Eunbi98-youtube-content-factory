from __future__ import annotations

import asyncio
import json
import math
import struct
import wave
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from audio_duration import measure_audio_duration
from tts_engine import EdgeTTSEngine


class QuizAudioPipelineError(RuntimeError):
    """Quiz 전용 오디오 생성 실패."""


@dataclass(frozen=True)
class QuizAudioResult:
    output_dir: Path
    generated_count: int
    reused_count: int
    tts_count: int
    countdown_count: int
    audio_files: tuple[Path, ...]


def _read_timeline(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, json.JSONDecodeError) as exc:
        raise QuizAudioPipelineError(
            f"Quiz Timeline을 읽지 못했습니다:\n{path}\n원인: {exc}"
        ) from exc

    if not isinstance(data, dict):
        raise QuizAudioPipelineError("Quiz Timeline 최상위 값은 객체여야 합니다.")

    scenes = data.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        raise QuizAudioPipelineError("Quiz Timeline에 scenes 배열이 없습니다.")

    return data


def _write_timeline(path: Path, data: dict[str, Any]) -> None:
    temporary = path.with_suffix(".json.tmp")
    try:
        temporary.write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        temporary.replace(path)
    except OSError as exc:
        if temporary.exists():
            temporary.unlink()
        raise QuizAudioPipelineError(
            f"Quiz Timeline 저장에 실패했습니다:\n{path}\n원인: {exc}"
        ) from exc


def _scene_type(scene: dict[str, Any]) -> str:
    raw_type = scene.get("sceneType") or scene.get("scene_type")
    if isinstance(raw_type, str) and raw_type.strip():
        return raw_type.strip().lower()

    scene_id = str(scene.get("id") or "").strip().lower()
    for candidate in ("question", "countdown", "answer", "intro", "ending"):
        if candidate in scene_id:
            return candidate
    return ""


def _scene_id(scene: dict[str, Any], index: int) -> str:
    raw_id = scene.get("id")
    if isinstance(raw_id, str) and raw_id.strip():
        return raw_id.strip()
    raise QuizAudioPipelineError(f"{index + 1}번째 Quiz Scene에 id가 없습니다.")


def _narration(scene: dict[str, Any]) -> str | None:
    raw = scene.get("narration")
    if not isinstance(raw, str):
        return None
    normalized = " ".join(raw.split())
    return normalized or None


def _duration_seconds(path: Path) -> float:
    result = measure_audio_duration(path)
    duration = getattr(result, "duration_seconds", result)
    try:
        numeric = float(duration)
    except (TypeError, ValueError) as exc:
        raise QuizAudioPipelineError(
            f"오디오 길이를 숫자로 변환하지 못했습니다: {path}"
        ) from exc
    if numeric <= 0:
        raise QuizAudioPipelineError(f"오디오 길이가 0초 이하입니다: {path}")
    return round(numeric, 3)


def _make_tick_wav(path: Path) -> float:
    sample_rate = 44100
    duration_seconds = 1.0
    beep_seconds = 0.18
    frequency = 960.0
    amplitude = 0.42
    frame_count = int(sample_rate * duration_seconds)
    beep_count = int(sample_rate * beep_seconds)

    samples: list[int] = []
    for index in range(frame_count):
        if index < beep_count:
            attack = min(1.0, index / 220.0)
            release = min(1.0, (beep_count - index) / 700.0)
            envelope = max(0.0, min(attack, release))
            value = amplitude * envelope * math.sin(
                2.0 * math.pi * frequency * index / sample_rate
            )
        else:
            value = 0.0
        samples.append(int(max(-1.0, min(1.0, value)) * 32767))

    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".wav.part")
    with wave.open(str(temporary), "wb") as writer:
        writer.setnchannels(1)
        writer.setsampwidth(2)
        writer.setframerate(sample_rate)
        writer.writeframes(b"".join(struct.pack("<h", sample) for sample in samples))
    temporary.replace(path)
    return duration_seconds


def _metadata_name(audio_path: Path) -> str:
    return f"{audio_path.stem}.timing.json"


def _numeric_seconds(value: Any, *, default: float = 0.0) -> float:
    if isinstance(value, (int, float)):
        return float(value)
    return default


def _capture_scene_gaps(scenes: list[Any]) -> tuple[list[float], float]:
    gaps: list[float] = []
    previous_end = 0.0

    for index, raw_scene in enumerate(scenes):
        if not isinstance(raw_scene, dict):
            gaps.append(0.0)
            continue

        start = _numeric_seconds(raw_scene.get("start"), default=previous_end)
        duration = max(0.0, _numeric_seconds(raw_scene.get("duration")))

        if index == 0:
            gaps.append(0.0)
        else:
            gaps.append(max(0.0, start - previous_end))

        previous_end = start + duration

    return gaps, previous_end


def _padding_for_role(role: str) -> float:
    if role == "question":
        return 0.25
    if role in {"answer", "ending"}:
        return 0.35
    return 0.0


def _reschedule_scenes(
    timeline: dict[str, Any],
    *,
    original_gaps: list[float],
    original_last_end: float,
) -> None:
    scenes = timeline.get("scenes")
    if not isinstance(scenes, list) or not scenes:
        return

    original_total = _numeric_seconds(timeline.get("totalDuration"))
    trailing_gap = max(0.0, original_total - original_last_end)
    previous_end = 0.0

    for index, raw_scene in enumerate(scenes):
        if not isinstance(raw_scene, dict):
            continue

        duration = max(0.001, _numeric_seconds(raw_scene.get("duration"), default=1.0))

        if index == 0:
            start = _numeric_seconds(raw_scene.get("start"))
        else:
            gap = original_gaps[index] if index < len(original_gaps) else 0.0
            start = previous_end + gap

        raw_scene["start"] = round(start, 3)
        raw_scene["duration"] = round(duration, 3)
        previous_end = start + duration

    timeline["totalDuration"] = round(previous_end + trailing_gap, 3)


class QuizAudioPipeline:
    """
    Quiz Scene별 오디오를 생성합니다.

    - question/answer/ending: Scene narration으로 개별 TTS 생성
    - countdown: 공용 1초 SFX 재사용
    - TTS 길이에 맞춰 Scene duration과 이후 start를 자동 재계산
    - Quiz 레이아웃은 변경하지 않음
    """

    def __init__(self, *, engine: EdgeTTSEngine) -> None:
        self.engine = engine

    async def generate(
        self,
        *,
        timeline_path: Path,
        output_dir: Path,
    ) -> QuizAudioResult:
        resolved_timeline = timeline_path.resolve()
        resolved_output = output_dir.resolve()
        timeline = _read_timeline(resolved_timeline)

        episode_id = str(timeline.get("episodeId") or resolved_timeline.parent.name).strip().lower()
        if not episode_id:
            raise QuizAudioPipelineError("Quiz Timeline의 episodeId가 비어 있습니다.")

        channel = str(timeline.get("channel") or "").strip().lower()
        if channel and channel != "quiz":
            raise QuizAudioPipelineError(
                f"Quiz Audio Pipeline에 quiz가 아닌 Timeline이 전달되었습니다: {channel}"
            )

        scenes = timeline["scenes"]
        original_gaps, original_last_end = _capture_scene_gaps(scenes)
        resolved_output.mkdir(parents=True, exist_ok=True)

        countdown_path = resolved_output / "quiz_countdown_tick.wav"
        countdown_existed = countdown_path.exists() and countdown_path.stat().st_size > 0
        countdown_duration = (
            _duration_seconds(countdown_path)
            if countdown_existed
            else _make_tick_wav(countdown_path)
        )

        generated_count = 0 if countdown_existed else 1
        reused_count = 1 if countdown_existed else 0
        tts_count = 0
        countdown_count = 0
        audio_files: list[Path] = [countdown_path]

        for index, raw_scene in enumerate(scenes):
            if not isinstance(raw_scene, dict):
                raise QuizAudioPipelineError(
                    f"{index + 1}번째 Quiz Scene이 객체가 아닙니다."
                )

            scene_id = _scene_id(raw_scene, index)
            role = _scene_type(raw_scene)

            raw_scene.pop("audioTimeline", None)

            if role == "countdown":
                raw_scene["audio"] = f"{episode_id}/audio/{countdown_path.name}"
                raw_scene["audioDuration"] = round(countdown_duration, 3)
                raw_scene.pop("timing", None)
                raw_scene.pop("wordTimings", None)
                raw_scene.pop("wordCount", None)
                raw_scene.pop("audioPlaybackRate", None)
                countdown_count += 1
                continue

            text = _narration(raw_scene)
            if not text:
                raw_scene.pop("audio", None)
                raw_scene.pop("audioDuration", None)
                raw_scene.pop("timing", None)
                raw_scene.pop("wordTimings", None)
                raw_scene.pop("wordCount", None)
                raw_scene.pop("audioPlaybackRate", None)
                continue

            expected_audio = self.engine.config.build_scene_path(
                output_dir=resolved_output,
                scene_id=scene_id,
            )
            expected_metadata = resolved_output / _metadata_name(expected_audio)
            cache_existed = (
                expected_audio.exists()
                and expected_audio.stat().st_size > 0
                and expected_metadata.exists()
                and expected_metadata.stat().st_size > 0
                and not self.engine.config.overwrite
            )

            generation = await self.engine.generate(
                scene_id=scene_id,
                text=text,
                output_dir=resolved_output,
            )
            audio_duration = _duration_seconds(generation.output_path)

            current_duration = max(
                0.001,
                _numeric_seconds(raw_scene.get("duration"), default=1.0),
            )
            required_duration = round(
                audio_duration + _padding_for_role(role),
                3,
            )
            raw_scene["duration"] = round(
                max(current_duration, required_duration),
                3,
            )

            raw_scene.pop("audioPlaybackRate", None)
            raw_scene["audio"] = f"{episode_id}/audio/{generation.output_path.name}"
            raw_scene["audioDuration"] = audio_duration
            raw_scene["timing"] = f"{episode_id}/audio/{generation.metadata_path.name}"
            raw_scene["wordTimings"] = [
                boundary.to_dict()
                for boundary in generation.word_boundaries
            ]
            raw_scene["wordCount"] = len(generation.word_boundaries)

            audio_files.append(generation.output_path)
            tts_count += 1
            if cache_existed:
                reused_count += 1
            else:
                generated_count += 1

        question_count = sum(
            1 for scene in scenes
            if isinstance(scene, dict) and _scene_type(scene) == "question"
        )
        answer_count = sum(
            1 for scene in scenes
            if isinstance(scene, dict) and _scene_type(scene) == "answer"
        )

        if question_count == 0 or answer_count == 0:
            raise QuizAudioPipelineError(
                "Question 또는 Answer Scene을 찾지 못했습니다."
            )
        if tts_count < question_count + answer_count:
            raise QuizAudioPipelineError(
                "모든 Question/Answer Scene에 narration이 존재하지 않습니다.\n"
                f"Question: {question_count}개, Answer: {answer_count}개, "
                f"생성 TTS Scene: {tts_count}개"
            )

        _reschedule_scenes(
            timeline,
            original_gaps=original_gaps,
            original_last_end=original_last_end,
        )

        timeline.pop("audioTimeline", None)
        timeline.pop("quizAudio", None)
        timeline["quizAudio"] = {
            "version": "8.3.2",
            "mode": "scene-audio-dynamic-duration",
            "questionCount": question_count,
            "answerCount": answer_count,
            "countdownSceneCount": countdown_count,
        }

        _write_timeline(resolved_timeline, timeline)

        return QuizAudioResult(
            output_dir=resolved_output,
            generated_count=generated_count,
            reused_count=reused_count,
            tts_count=tts_count,
            countdown_count=countdown_count,
            audio_files=tuple(audio_files),
        )

    def generate_sync(
        self,
        *,
        timeline_path: Path,
        output_dir: Path,
    ) -> QuizAudioResult:
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.generate(
                    timeline_path=timeline_path,
                    output_dir=output_dir,
                )
            )
        raise QuizAudioPipelineError(
            "실행 중인 asyncio 이벤트 루프가 있습니다. "
            "비동기 환경에서는 await generate(...)를 사용하세요."
        )
