from __future__ import annotations

from dataclasses import dataclass

from story_graph import Story


@dataclass(frozen=True)
class StoryValidationResult:
    is_valid: bool
    score: float
    errors: list[str]
    warnings: list[str]


class StoryValidator:
    REQUIRED_TYPES = ["hook", "answer", "story", "fact", "ending"]

    def validate(self, story: Story) -> StoryValidationResult:
        errors: list[str] = []
        warnings: list[str] = []
        score = 100.0

        if [beat.type for beat in story.beats] != self.REQUIRED_TYPES:
            errors.append("Beat 순서는 hook, answer, story, fact, ending이어야 합니다.")
            score -= 35.0

        if len(story.beats) != 5:
            errors.append("Mystery Story는 5개의 Beat가 필요합니다.")
            score -= 25.0

        if story.beats:
            if not story.beats[0].narration.strip().endswith("?"):
                warnings.append("Hook narration이 질문으로 끝나지 않습니다.")
                score -= 10.0
            if len(story.beats[0].title.strip()) > 30:
                warnings.append("Hook title이 30자를 초과합니다.")
                score -= 5.0
            if not story.beats[-1].narration.strip().endswith("?"):
                warnings.append("Ending narration이 의견 질문으로 끝나지 않습니다.")
                score -= 10.0

        for index, beat in enumerate(story.beats, start=1):
            if not beat.title.strip():
                errors.append(f"Beat {index}: title이 비어 있습니다.")
                score -= 10.0
            if not beat.narration.strip():
                errors.append(f"Beat {index}: narration이 비어 있습니다.")
                score -= 15.0
            if not beat.subtitle.strip():
                errors.append(f"Beat {index}: subtitle이 비어 있습니다.")
                score -= 10.0
            if len(beat.subtitle.replace("\n", "")) > 40:
                warnings.append(f"Beat {index}: subtitle이 너무 깁니다.")
                score -= 3.0

        return StoryValidationResult(
            is_valid=not errors,
            score=round(max(score, 0.0), 1),
            errors=errors,
            warnings=warnings,
        )

    def validate_or_raise(self, story: Story) -> StoryValidationResult:
        result = self.validate(story)
        if not result.is_valid:
            raise ValueError("Story 품질 검사 실패: " + " | ".join(result.errors))
        return result
