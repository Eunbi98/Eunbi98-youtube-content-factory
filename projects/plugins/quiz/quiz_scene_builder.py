from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any


class QuizSceneBuildError(ValueError):
    """퀴즈 장면 데이터 생성 실패."""


@dataclass(frozen=True)
class QuizAudioEvent:
    event_type: str
    source_type: str
    text: str | None
    sound_effect: str | None
    start_offset: float

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class QuizScene:
    id: str
    scene_type: str
    question_id: str | None
    order: int
    duration: float
    title: str
    display_text: str
    tts_text: str | None
    audio_events: tuple[QuizAudioEvent, ...]
    metadata: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "scene_type": self.scene_type,
            "question_id": self.question_id,
            "order": self.order,
            "duration": self.duration,
            "title": self.title,
            "display_text": self.display_text,
            "tts_text": self.tts_text,
            "audio_events": [
                event.to_dict()
                for event in self.audio_events
            ],
            "metadata": self.metadata,
        }


@dataclass(frozen=True)
class QuizSceneCollection:
    episode_id: str
    genre: str
    title: str
    fps: int
    width: int
    height: int
    total_duration: float
    scene_count: int
    scenes: tuple[QuizScene, ...]

    def to_dict(self) -> dict[str, Any]:
        return {
            "episode_id": self.episode_id,
            "genre": self.genre,
            "title": self.title,
            "fps": self.fps,
            "width": self.width,
            "height": self.height,
            "total_duration": self.total_duration,
            "scene_count": self.scene_count,
            "scenes": [
                scene.to_dict()
                for scene in self.scenes
            ],
        }


class QuizSceneBuilder:
    INTRO_DURATION = 2.0
    QUESTION_DURATION = 4.0
    COUNTDOWN_DURATION = 3.0
    ANSWER_DURATION = 2.5
    ENDING_DURATION = 2.5

    FPS = 30
    WIDTH = 1080
    HEIGHT = 1920

    def load_quiz_story(
        self,
        story_path: Path,
    ) -> dict[str, Any]:
        resolved_path = story_path.resolve()

        if not resolved_path.exists():
            raise FileNotFoundError(
                f"Quiz Story 파일이 없습니다: "
                f"{resolved_path}"
            )

        try:
            with resolved_path.open(
                "r",
                encoding="utf-8",
            ) as file:
                data = json.load(file)
        except json.JSONDecodeError as error:
            raise QuizSceneBuildError(
                "quiz_story.json 형식이 "
                f"올바르지 않습니다: {error}"
            ) from error

        if not isinstance(data, dict):
            raise QuizSceneBuildError(
                "quiz_story.json 최상위 값은 "
                "객체여야 합니다."
            )

        return data

    def build_from_file(
        self,
        story_path: Path,
        output_path: Path,
    ) -> QuizSceneCollection:
        story = self.load_quiz_story(
            story_path
        )
        collection = self.build(story)
        self.write_output(
            collection=collection,
            output_path=output_path,
        )
        return collection

    def build(
        self,
        story: dict[str, Any],
    ) -> QuizSceneCollection:
        episode_id = self._require_text(
            story.get("episode_id"),
            "episode_id",
        )
        genre = self._require_text(
            story.get("genre"),
            "genre",
        )
        title = self._require_text(
            story.get("title"),
            "title",
        )

        if genre != "quiz":
            raise QuizSceneBuildError(
                "genre는 quiz여야 합니다."
            )

        raw_questions = story.get("questions")

        if not isinstance(raw_questions, list):
            raise QuizSceneBuildError(
                "questions는 배열이어야 합니다."
            )

        if not raw_questions:
            raise QuizSceneBuildError(
                "장면을 생성할 문제가 없습니다."
            )

        scenes: list[QuizScene] = []
        order = 1

        scenes.append(
            self._build_intro_scene(
                order=order,
                title=title,
            )
        )
        order += 1

        for question_number, question in enumerate(
            raw_questions,
            start=1,
        ):
            if not isinstance(question, dict):
                raise QuizSceneBuildError(
                    f"{question_number}번 문제 데이터가 "
                    "객체가 아닙니다."
                )

            question_id = self._require_text(
                question.get("id"),
                f"questions[{question_number - 1}].id",
            )
            question_text = self._require_text(
                question.get("question"),
                f"{question_id}.question",
            )
            answer = self._require_text(
                question.get("answer"),
                f"{question_id}.answer",
            )
            question_tts = self._require_text(
                question.get("question_tts"),
                f"{question_id}.question_tts",
            )
            answer_tts = self._require_text(
                question.get("answer_tts"),
                f"{question_id}.answer_tts",
            )

            countdown_seconds = question.get(
                "countdown_seconds"
            )

            if countdown_seconds != 3:
                raise QuizSceneBuildError(
                    f"{question_id}: 카운트다운은 "
                    "3초여야 합니다."
                )

            scenes.append(
                self._build_question_scene(
                    order=order,
                    question_number=question_number,
                    question_id=question_id,
                    question_text=question_text,
                    question_tts=question_tts,
                    category=str(
                        question.get(
                            "category",
                            "general",
                        )
                    ),
                    difficulty=str(
                        question.get(
                            "difficulty",
                            "normal",
                        )
                    ),
                )
            )
            order += 1

            scenes.append(
                self._build_countdown_scene(
                    order=order,
                    question_number=question_number,
                    question_id=question_id,
                )
            )
            order += 1

            scenes.append(
                self._build_answer_scene(
                    order=order,
                    question_number=question_number,
                    question_id=question_id,
                    answer=answer,
                    answer_tts=answer_tts,
                )
            )
            order += 1

        ending = story.get("ending", {})

        if not isinstance(ending, dict):
            raise QuizSceneBuildError(
                "ending은 객체여야 합니다."
            )

        ending_text = self._require_text(
            ending.get(
                "text",
                "몇 문제를 맞혔나요?",
            ),
            "ending.text",
        )
        ending_tts = self._require_text(
            ending.get(
                "tts",
                "몇 문제를 맞혔는지 "
                "댓글로 남겨주세요.",
            ),
            "ending.tts",
        )

        scenes.append(
            self._build_ending_scene(
                order=order,
                ending_text=ending_text,
                ending_tts=ending_tts,
            )
        )

        total_duration = round(
            sum(
                scene.duration
                for scene in scenes
            ),
            3,
        )

        return QuizSceneCollection(
            episode_id=episode_id,
            genre="quiz",
            title=title,
            fps=self.FPS,
            width=self.WIDTH,
            height=self.HEIGHT,
            total_duration=total_duration,
            scene_count=len(scenes),
            scenes=tuple(scenes),
        )

    def write_output(
        self,
        collection: QuizSceneCollection,
        output_path: Path,
    ) -> None:
        resolved_path = output_path.resolve()
        resolved_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary_path = resolved_path.with_suffix(
            resolved_path.suffix + ".tmp"
        )

        with temporary_path.open(
            "w",
            encoding="utf-8",
            newline="\n",
        ) as file:
            json.dump(
                collection.to_dict(),
                file,
                ensure_ascii=False,
                indent=2,
            )
            file.write("\n")

        temporary_path.replace(
            resolved_path
        )

    def _build_intro_scene(
        self,
        *,
        order: int,
        title: str,
    ) -> QuizScene:
        return QuizScene(
            id="quiz_intro",
            scene_type="intro",
            question_id=None,
            order=order,
            duration=self.INTRO_DURATION,
            title="오늘의 퀴즈",
            display_text=title,
            tts_text=None,
            audio_events=(
                QuizAudioEvent(
                    event_type="quiz_intro",
                    source_type="sound_effect",
                    text=None,
                    sound_effect="quiz_intro",
                    start_offset=0.0,
                ),
            ),
            metadata={
                "tts_enabled": False,
                "show_question_number": False,
            },
        )

    def _build_question_scene(
        self,
        *,
        order: int,
        question_number: int,
        question_id: str,
        question_text: str,
        question_tts: str,
        category: str,
        difficulty: str,
    ) -> QuizScene:
        return QuizScene(
            id=f"{question_id}_question",
            scene_type="question",
            question_id=question_id,
            order=order,
            duration=self.QUESTION_DURATION,
            title=f"문제 {question_number}",
            display_text=question_text,
            tts_text=question_tts,
            audio_events=(
                QuizAudioEvent(
                    event_type="question_tts",
                    source_type="tts",
                    text=question_tts,
                    sound_effect=None,
                    start_offset=0.15,
                ),
            ),
            metadata={
                "question_number": question_number,
                "category": category,
                "difficulty": difficulty,
                "max_display_lines": 2,
                "tts_enabled": True,
            },
        )

    def _build_countdown_scene(
        self,
        *,
        order: int,
        question_number: int,
        question_id: str,
    ) -> QuizScene:
        return QuizScene(
            id=f"{question_id}_countdown",
            scene_type="countdown",
            question_id=question_id,
            order=order,
            duration=self.COUNTDOWN_DURATION,
            title=f"문제 {question_number}",
            display_text="3",
            tts_text=None,
            audio_events=(
                QuizAudioEvent(
                    event_type="countdown_tick",
                    source_type="sound_effect",
                    text=None,
                    sound_effect="countdown_tick",
                    start_offset=0.0,
                ),
                QuizAudioEvent(
                    event_type="countdown_tick",
                    source_type="sound_effect",
                    text=None,
                    sound_effect="countdown_tick",
                    start_offset=1.0,
                ),
                QuizAudioEvent(
                    event_type="countdown_tick",
                    source_type="sound_effect",
                    text=None,
                    sound_effect="countdown_tick",
                    start_offset=2.0,
                ),
            ),
            metadata={
                "question_number": question_number,
                "countdown_seconds": 3,
                "countdown_values": [3, 2, 1],
                "tts_enabled": False,
            },
        )

    def _build_answer_scene(
        self,
        *,
        order: int,
        question_number: int,
        question_id: str,
        answer: str,
        answer_tts: str,
    ) -> QuizScene:
        return QuizScene(
            id=f"{question_id}_answer",
            scene_type="answer",
            question_id=question_id,
            order=order,
            duration=self.ANSWER_DURATION,
            title="정답",
            display_text=answer,
            tts_text=answer_tts,
            audio_events=(
                QuizAudioEvent(
                    event_type="answer_reveal",
                    source_type="sound_effect",
                    text=None,
                    sound_effect="answer_reveal",
                    start_offset=0.0,
                ),
                QuizAudioEvent(
                    event_type="answer_tts",
                    source_type="tts",
                    text=answer_tts,
                    sound_effect=None,
                    start_offset=0.2,
                ),
            ),
            metadata={
                "question_number": question_number,
                "tts_enabled": True,
                "explanation_enabled": False,
            },
        )

    def _build_ending_scene(
        self,
        *,
        order: int,
        ending_text: str,
        ending_tts: str,
    ) -> QuizScene:
        return QuizScene(
            id="quiz_ending",
            scene_type="ending",
            question_id=None,
            order=order,
            duration=self.ENDING_DURATION,
            title="오늘의 결과",
            display_text=ending_text,
            tts_text=ending_tts,
            audio_events=(
                QuizAudioEvent(
                    event_type="ending_tts",
                    source_type="tts",
                    text=ending_tts,
                    sound_effect=None,
                    start_offset=0.1,
                ),
            ),
            metadata={
                "tts_enabled": True,
                "show_question_number": False,
            },
        )

    @staticmethod
    def _require_text(
        value: Any,
        field_name: str,
    ) -> str:
        if not isinstance(value, str):
            raise QuizSceneBuildError(
                f"{field_name}은 문자열이어야 합니다."
            )

        cleaned = " ".join(
            value.strip().split()
        )

        if not cleaned:
            raise QuizSceneBuildError(
                f"{field_name}은 비어 있을 수 없습니다."
            )

        return cleaned