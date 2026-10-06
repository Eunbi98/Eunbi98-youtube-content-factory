from __future__ import annotations

from dataclasses import dataclass, replace

from hook_generator import HookCandidate, HookGenerator
from story_graph import Beat, Story
from story_validator import StoryValidationResult, StoryValidator


@dataclass(frozen=True)
class StoryOptimizationResult:
    story: Story
    selected_hook: HookCandidate
    validation: StoryValidationResult


class StoryOptimizer:
    def __init__(
        self,
        *,
        hook_generator: HookGenerator | None = None,
        story_validator: StoryValidator | None = None,
    ) -> None:
        self._hook_generator = hook_generator or HookGenerator()
        self._story_validator = story_validator or StoryValidator()

    def optimize(self, *, story: Story, topic: str) -> StoryOptimizationResult:
        if not story.beats:
            raise ValueError("최적화할 Story Beat가 없습니다.")

        selected_hook = self._hook_generator.best(topic=topic)
        original_hook = story.beats[0]

        optimized_hook = Beat(
            type=original_hook.type,
            title=selected_hook.text,
            narration=f"{selected_hook.text} {original_hook.narration.strip()}",
            subtitle=self._subtitle_from_hook(selected_hook.text),
            media=original_hook.media,
            keywords=list(original_hook.keywords),
            background_color=original_hook.background_color,
        )

        optimized_story = replace(
            story,
            title=selected_hook.text,
            beats=[optimized_hook, *story.beats[1:]],
        )

        validation = self._story_validator.validate_or_raise(optimized_story)

        return StoryOptimizationResult(
            story=optimized_story,
            selected_hook=selected_hook,
            validation=validation,
        )

    @staticmethod
    def _subtitle_from_hook(text: str) -> str:
        text = text.strip()
        if len(text) <= 18:
            return text

        midpoint = len(text) // 2
        split_index = text.rfind(" ", 0, midpoint + 1)
        if split_index <= 0:
            split_index = text.find(" ", midpoint)
        if split_index <= 0:
            return text

        return text[:split_index].strip() + "\n" + text[split_index:].strip()
