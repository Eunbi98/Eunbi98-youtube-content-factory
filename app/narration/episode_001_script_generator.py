from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


FINAL_NARRATION = """사람이 382일 동안 우주에 있으면?

가장 먼저 망가지는 건
근육일까요?

아닙니다.

먼저 문제가 생길 수 있는 곳은
눈입니다.

우주에서는 중력이 거의 없어서
몸속의 체액이 머리 쪽으로 몰립니다.

그래서 눈이 평소와 다르게
보이기 시작할 수 있습니다.

더 놀라운 건 뼈가
매달 1~1.5%씩 줄어든다는 겁니다.

그래서 우주비행사들은
매일 2시간 가까이 운동합니다.

운동은 선택이 아니라
몸을 버티게 하는 루틴입니다.

그런데도 지구로 돌아오면
걷는 것부터 다시 적응해야 합니다.

인간의 몸은
지구에 맞춰져 있기 때문입니다.

그렇다면
화성에서는 어떻게 될까요?"""


@dataclass(frozen=True)
class EpisodeScriptResult:
    episode_id: str
    markdown_path: str
    json_path: str
    line_count: int


class Episode001ScriptGenerator:
    REQUIRED_INPUTS = (
        "knowledge_pack.json",
        "story_beats.json",
        "beat_sheet.json",
    )

    def generate(self, episode_dir: Path | str) -> EpisodeScriptResult:
        target_dir = Path(episode_dir)
        self._ensure_required_inputs(target_dir)

        markdown_path = target_dir / "script.md"
        json_path = target_dir / "script.json"
        narration_lines = self._split_narration_lines(FINAL_NARRATION)

        markdown_path.write_text(FINAL_NARRATION + "\n", encoding="utf-8")
        json_path.write_text(
            json.dumps(
                {
                    "episode_id": "episode_001",
                    "narration_lines": narration_lines,
                    "caption_text": FINAL_NARRATION,
                    "source_inputs": list(self.REQUIRED_INPUTS),
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )

        return EpisodeScriptResult(
            episode_id="episode_001",
            markdown_path=str(markdown_path),
            json_path=str(json_path),
            line_count=len(narration_lines),
        )

    def _ensure_required_inputs(self, episode_dir: Path) -> None:
        missing = [
            filename
            for filename in self.REQUIRED_INPUTS
            if not (episode_dir / filename).exists()
        ]
        if missing:
            raise FileNotFoundError(f"Missing Episode 001 inputs: {missing}")

    def _split_narration_lines(self, narration: str) -> list[str]:
        return [
            block.strip()
            for block in narration.split("\n\n")
            if block.strip()
        ]
