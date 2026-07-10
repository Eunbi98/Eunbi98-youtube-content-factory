from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.beat_sheet.beat_sheet_types import Beat, BeatSheet, BeatSheetGenerationResult
from app.video.caption_layout import layout_caption_text


class Episode001BeatSheetGenerator:
    REQUIRED_KNOWLEDGE_FIELDS = (
        "episode_id",
        "main_question",
        "verified_facts",
        "story_materials",
        "sources",
    )
    REQUIRED_STORY_FIELDS = (
        "hook",
        "misconception",
        "reveal",
        "explanation",
        "second_reveal",
        "human_moment",
        "next_episode_hook",
    )

    def generate_from_files(
        self,
        knowledge_pack_path: Path | str,
        story_beats_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> BeatSheetGenerationResult:
        knowledge_pack_file = Path(knowledge_pack_path)
        story_beats_file = Path(story_beats_path)
        target_dir = Path(output_dir) if output_dir else knowledge_pack_file.parent

        knowledge_pack = self._load_json(knowledge_pack_file)
        story_beats = self._load_json(story_beats_file)
        beat_sheet = self.generate(knowledge_pack, story_beats)

        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / "beat_sheet.json"
        markdown_path = target_dir / "beat_sheet.md"

        json_path.write_text(
            json.dumps(beat_sheet.to_dict(), ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(
            self._render_markdown(beat_sheet),
            encoding="utf-8",
        )

        return BeatSheetGenerationResult(
            episode_id=beat_sheet.episode_id,
            json_path=str(json_path),
            markdown_path=str(markdown_path),
            duration_seconds=beat_sheet.duration_seconds,
        )

    def generate(
        self,
        knowledge_pack: dict[str, Any],
        story_beats: dict[str, Any],
    ) -> BeatSheet:
        self._validate(knowledge_pack, self.REQUIRED_KNOWLEDGE_FIELDS, "knowledge_pack")
        self._validate(story_beats, self.REQUIRED_STORY_FIELDS, "story_beats")
        self._assert_verified_basis(knowledge_pack)

        beat_specs = [
            {
                "start_time": 0,
                "end_time": 3,
                "purpose": "Hook",
                "narration_intent": "382일이라는 질문을 즉시 던지고 시청자의 호기심을 붙잡는다.",
                "caption_text": story_beats["hook"],
                "visual_direction": "검은 화면에서 382일 카운터와 ISS 실루엣을 빠르게 등장시킨다.",
                "emotion": "curiosity",
                "transition_note": "숫자에서 사람들의 첫 오해로 빠르게 전환한다.",
            },
            {
                "start_time": 3,
                "end_time": 8,
                "purpose": "오해",
                "narration_intent": "시청자가 예상하기 쉬운 근육 붕괴 프레임을 먼저 제시한다.",
                "caption_text": "사람들은 근육부터\n망가진다고 생각한다.",
                "visual_direction": "근육 실루엣과 약해지는 게이지를 보여주되 결론처럼 보이지 않게 처리한다.",
                "emotion": "assumption",
                "transition_note": "근육 이미지에서 눈 클로즈업으로 반전 전환한다.",
            },
            {
                "start_time": 8,
                "end_time": 14,
                "purpose": "반전",
                "narration_intent": "가장 먼저 주목할 문제가 눈일 수 있다는 반전을 제시한다.",
                "caption_text": "먼저 문제는 눈에서\n시작될 수 있다.",
                "visual_direction": "우주비행사 헬멧 바이저 안쪽의 눈과 시야 왜곡 그래픽을 겹친다.",
                "emotion": "surprise",
                "transition_note": "눈에서 머리 쪽 체액 이동 도식으로 이어간다.",
            },
            {
                "start_time": 14,
                "end_time": 24,
                "purpose": "이유 설명",
                "narration_intent": "미세중력, 체액 이동, 시야 변화의 연결을 한 번에 이해시키는 구간이다.",
                "caption_text": "체액이 머리로 이동한다.\n시야 변화로 이어질 수 있다.",
                "visual_direction": "몸 아래쪽에서 머리 쪽으로 이동하는 체액 화살표와 시야 변화 아이콘을 배치한다.",
                "emotion": "understanding",
                "transition_note": "머리 쪽 변화에서 전신 변화로 화면을 넓힌다.",
            },
            {
                "start_time": 24,
                "end_time": 36,
                "purpose": "뼈/근육 변화",
                "narration_intent": "눈의 반전 이후, 뼈와 근육도 실제로 약해진다는 근거를 덧붙인다.",
                "caption_text": "뼈와 근육도 약해진다.\n골밀도는 월 1~1.5% 손실될 수 있다.",
                "visual_direction": "골밀도 그래프, 근육량 게이지, 1~1.5% 수치를 크게 보여준다.",
                "emotion": "concern",
                "transition_note": "약해지는 몸에서 버티는 루틴으로 분위기를 바꾼다.",
            },
            {
                "start_time": 36,
                "end_time": 46,
                "purpose": "우주비행사 생존 루틴",
                "narration_intent": "장기 체류는 버티는 일이 아니라 매일 관리하는 루틴이라는 점을 보여준다.",
                "caption_text": "Scott Kelly 340일.\nFrank Rubio 371일.",
                "visual_direction": "ISS 운동 장비, 체크리스트, Scott Kelly와 Frank Rubio 체류 기간 막대를 보여준다.",
                "emotion": "resilience",
                "transition_note": "우주에서 버틴 몸이 지구로 돌아오는 장면으로 전환한다.",
            },
            {
                "start_time": 46,
                "end_time": 55,
                "purpose": "지구 귀환 후 재적응",
                "narration_intent": "우주에 적응한 몸이 귀환 뒤 다시 중력을 배워야 한다는 인간적 순간을 만든다.",
                "caption_text": "우주에 적응한 몸은\n지구에서 다시 적응한다.",
                "visual_direction": "귀환 캡슐, 재활 보행, 균형 테스트, 시야 검사 이미지를 차례로 연결한다.",
                "emotion": "empathy",
                "transition_note": "재적응 장면을 다음 질문으로 열어둔다.",
            },
            {
                "start_time": 55,
                "end_time": 60,
                "purpose": "다음 질문",
                "narration_intent": "화성이라는 다음 조건을 던져 에피소드 확장 여지를 남긴다.",
                "caption_text": "화성에서는 더 심해질까요?",
                "visual_direction": "지구와 화성을 나란히 놓고 중력 차이를 암시하는 그래픽으로 마무리한다.",
                "emotion": "wonder",
                "transition_note": "질문형 엔딩으로 끊는다.",
            },
        ]

        beats = [
            self._build_beat(spec)
            for spec in beat_specs
        ]
        return BeatSheet(
            episode_id=str(knowledge_pack["episode_id"]),
            duration_seconds=beats[-1].end_time,
            beats=beats,
        )

    def _build_beat(self, spec: dict[str, Any]) -> Beat:
        caption_text = self._layout_caption(str(spec["caption_text"]))
        return Beat(
            start_time=int(spec["start_time"]),
            end_time=int(spec["end_time"]),
            purpose=str(spec["purpose"]),
            narration_intent=str(spec["narration_intent"]),
            caption_text=caption_text,
            visual_direction=str(spec["visual_direction"]),
            emotion=str(spec["emotion"]),
            transition_note=str(spec["transition_note"]),
        )

    def _layout_caption(self, text: str) -> str:
        sentences = [
            sentence.strip()
            for sentence in str(text).splitlines()
            if sentence.strip()
        ]
        if len(sentences) > 1:
            return "\n".join(sentences[:2])

        return layout_caption_text(
            text,
            one_line_max=28,
            preferred_min=14,
            preferred_max=18,
            two_line_max=48,
            min_second_line=8,
        )

    def _load_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object.")
        return data

    def _validate(
        self,
        data: dict[str, Any],
        required_fields: tuple[str, ...],
        label: str,
    ) -> None:
        missing = [
            field
            for field in required_fields
            if field not in data
        ]
        if missing:
            raise ValueError(f"{label} is missing fields: {missing}")

    def _assert_verified_basis(self, knowledge_pack: dict[str, Any]) -> None:
        verified_text = "\n".join(
            str(item)
            for item in knowledge_pack.get("verified_facts", [])
        )
        required_term_groups = (
            ("미세중력",),
            ("체액",),
            ("시야", "시각"),
            ("골밀도",),
            ("근육",),
        )
        missing = [
            " or ".join(term_group)
            for term_group in required_term_groups
            if not any(term in verified_text for term in term_group)
        ]
        if missing:
            raise ValueError(f"Verified facts do not support beat sheet terms: {missing}")

    def _render_markdown(self, beat_sheet: BeatSheet) -> str:
        lines = [
            "# Episode 001 Beat Sheet",
            "",
            f"- Duration: {beat_sheet.duration_seconds}s",
            f"- Beat count: {len(beat_sheet.beats)}",
            "",
            "| Time | Purpose | Caption | Visual | Emotion | Transition |",
            "| --- | --- | --- | --- | --- | --- |",
        ]

        for beat in beat_sheet.beats:
            caption = beat.caption_text.replace("\n", "<br>")
            lines.append(
                "| "
                f"{beat.start_time}~{beat.end_time}s | "
                f"{beat.purpose} | "
                f"{caption} | "
                f"{beat.visual_direction} | "
                f"{beat.emotion} | "
                f"{beat.transition_note} |"
            )

        lines.extend([
            "",
            "## Narration Intent",
            "",
        ])

        for beat in beat_sheet.beats:
            lines.append(
                f"- {beat.start_time}~{beat.end_time}s "
                f"{beat.purpose}: {beat.narration_intent}"
            )

        lines.append("")
        return "\n".join(lines)
