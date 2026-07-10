from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.scene_timeline.scene_timeline_types import (
    BGM_ENERGY_LEVELS,
    CAMERA_MOTIONS,
    RECOMMENDED_ASSET_TYPES,
    TRANSITIONS,
    SceneTimelineItem,
)


class SceneTimelineGenerator:
    REQUIRED_KNOWLEDGE_FIELDS = (
        "episode_id",
        "main_question",
        "verified_facts",
        "visual_ideas",
        "sources",
    )
    REQUIRED_STORY_FIELDS = (
        "hook",
        "misconception",
        "reveal",
        "explanation",
        "second_reveal",
        "human_moment",
        "surprising_fact",
        "ending",
        "next_episode_hook",
    )

    def generate_from_files(
        self,
        knowledge_pack_path: Path | str,
        story_beats_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> dict[str, object]:
        knowledge_pack_file = Path(knowledge_pack_path)
        story_beats_file = Path(story_beats_path)
        target_dir = Path(output_dir) if output_dir else knowledge_pack_file.parent

        knowledge_pack = self._load_json(knowledge_pack_file)
        story_beats = self._load_json(story_beats_file)
        timeline = self.generate(knowledge_pack, story_beats)

        target_dir.mkdir(parents=True, exist_ok=True)
        json_path = target_dir / "scene_timeline.json"
        markdown_path = target_dir / "scene_timeline.md"

        json_path.write_text(
            json.dumps(timeline, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        markdown_path.write_text(
            self._render_markdown(timeline),
            encoding="utf-8",
        )

        return timeline

    def generate(
        self,
        knowledge_pack: dict[str, Any],
        story_beats: dict[str, Any],
    ) -> dict[str, object]:
        self._validate(knowledge_pack, self.REQUIRED_KNOWLEDGE_FIELDS, "knowledge_pack")
        self._validate(story_beats, self.REQUIRED_STORY_FIELDS, "story_beats")

        scene_specs = self._episode_002_specs(story_beats)
        scenes: list[SceneTimelineItem] = []
        start_time = 0.0
        for index, spec in enumerate(scene_specs, start=1):
            scene = self._build_scene(index, spec, start_time)
            scenes.append(scene)
            start_time = scene.end_time

        return {
            "episode_id": str(knowledge_pack["episode_id"]),
            "timeline_version": 1,
            "source_inputs": [
                "knowledge_pack.json",
                "story_beats.json",
            ],
            "total_duration": scenes[-1].end_time if scenes else 0,
            "scene_count": len(scenes),
            "style_reference": "ORIGIN_EPISODE_001_MASTER_REFERENCE",
            "scenes": [scene.to_dict() for scene in scenes],
            "editing_rules": [
                "Design visual rhythm before final narration.",
                "Use short ORIGIN-style captions with one strong idea per scene.",
                "Prefer official NOAA/NASA/Wikimedia material for real deep-sea footage.",
                "Use infographics for invisible pressure and depth concepts.",
                "Keep transitions simple: cuts for reveals, cross dissolves for descent, dip to black for ending.",
            ],
        }

    def _episode_002_specs(self, story_beats: dict[str, Any]) -> list[dict[str, object]]:
        return [
            {
                "duration": 2.0,
                "purpose": "Hook",
                "narration": story_beats["hook"],
                "caption": "바다 11,000m\n까지 내려가면?",
                "recommended_asset_type": "official_video",
                "camera_motion": "slow_zoom_in",
                "transition": "cut",
                "sfx": "deep whoosh",
                "bgm_energy": "high",
            },
            {
                "duration": 2.0,
                "purpose": "Misconception",
                "narration": story_beats["misconception"],
                "caption": "먼저 위험한 건\n추위일까요?",
                "recommended_asset_type": "animation",
                "camera_motion": "static",
                "transition": "cut",
                "sfx": "cold hit",
                "bgm_energy": "medium",
            },
            {
                "duration": 2.0,
                "purpose": "Reveal",
                "narration": story_beats["reveal"],
                "caption": "아닙니다.\n먼저 압력입니다.",
                "recommended_asset_type": "infographic",
                "camera_motion": "push_in",
                "transition": "cut",
                "sfx": "pressure thump",
                "bgm_energy": "high",
            },
            {
                "duration": 3.0,
                "purpose": "Pressure Scale",
                "narration": story_beats["explanation"],
                "caption": "지상보다\n천 배 이상",
                "recommended_asset_type": "infographic",
                "camera_motion": "slow_zoom_in",
                "transition": "cross_dissolve",
                "sfx": "low rumble",
                "bgm_energy": "high",
            },
            {
                "duration": 3.0,
                "purpose": "Submersible Rule",
                "narration": story_beats["second_reveal"],
                "caption": "인간은\n잠수정 안에 있어야 합니다.",
                "recommended_asset_type": "official_video",
                "camera_motion": "slow_zoom_out",
                "transition": "cross_dissolve",
                "sfx": "metal creak",
                "bgm_energy": "medium",
            },
            {
                "duration": 3.0,
                "purpose": "Human Scale",
                "narration": story_beats["human_moment"],
                "caption": "작은 금속 방만이\n안전한 공간입니다.",
                "recommended_asset_type": "animation",
                "camera_motion": "static",
                "transition": "cross_dissolve",
                "sfx": "heartbeat low",
                "bgm_energy": "low",
            },
            {
                "duration": 4.0,
                "purpose": "Wonder",
                "narration": story_beats["surprising_fact"],
                "caption": "그 어둠 속에도\n생물은 살아 있습니다.",
                "recommended_asset_type": "official_video",
                "camera_motion": "pan_right",
                "transition": "cross_dissolve",
                "sfx": "water shimmer",
                "bgm_energy": "medium",
            },
            {
                "duration": 3.0,
                "purpose": "Ending Question",
                "narration": story_beats["next_episode_hook"],
                "caption": "바다에는\n더 깊은 곳이 있을까요?",
                "recommended_asset_type": "official_image",
                "camera_motion": "slow_zoom_out",
                "transition": "dip_to_black",
                "sfx": "distant drop",
                "bgm_energy": "low",
            },
        ]

    def _build_scene(
        self,
        index: int,
        spec: dict[str, object],
        start_time: float,
    ) -> SceneTimelineItem:
        duration = float(spec["duration"])
        end_time = round(start_time + duration, 3)
        item = SceneTimelineItem(
            scene_id=f"scene_{index:02d}",
            duration=duration,
            start_time=start_time,
            end_time=end_time,
            purpose=str(spec["purpose"]),
            narration=str(spec["narration"]),
            caption=str(spec["caption"]),
            recommended_asset_type=str(spec["recommended_asset_type"]),
            camera_motion=str(spec["camera_motion"]),
            transition=str(spec["transition"]),
            sfx=str(spec["sfx"]),
            bgm_energy=str(spec["bgm_energy"]),
        )
        self._validate_scene(item)
        return item

    def _render_markdown(self, timeline: dict[str, object]) -> str:
        lines = [
            "# Scene Timeline",
            "",
            f"- Episode: {timeline['episode_id']}",
            f"- Total Duration: {timeline['total_duration']}s",
            f"- Scene Count: {timeline['scene_count']}",
            "- Render: not generated",
            "",
            "## Premiere Edit Guide",
            "",
        ]

        for scene in timeline["scenes"]:
            lines.extend(
                [
                    f"### {scene['scene_id']}",
                    f"- Time: {scene['start_time']}s ~ {scene['end_time']}s ({scene['duration']}s)",
                    f"- Purpose: {scene['purpose']}",
                    f"- Narration: {scene['narration']}",
                    f"- Caption:",
                    "```",
                    str(scene["caption"]),
                    "```",
                    f"- Recommended Asset: {scene['recommended_asset_type']}",
                    f"- Camera Motion: {scene['camera_motion']}",
                    f"- Transition: {scene['transition']}",
                    f"- SFX: {scene['sfx']}",
                    f"- BGM Energy: {scene['bgm_energy']}",
                    "",
                ]
            )

        lines.extend(
            [
                "## Repeatable Rules",
                "",
                "- Keep each scene to one visual idea.",
                "- Use official_video for deep-sea footage and submersible scenes.",
                "- Use infographic for depth, pressure, and comparison numbers.",
                "- Use animation when the concept is invisible or internal.",
                "- End on a question with dip_to_black.",
                "",
            ]
        )
        return "\n".join(lines)

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
        missing = [field for field in required_fields if field not in data]
        if missing:
            raise ValueError(f"{label} is missing fields: {missing}")

    def _validate_scene(self, item: SceneTimelineItem) -> None:
        if item.camera_motion not in CAMERA_MOTIONS:
            raise ValueError(f"Invalid camera_motion: {item.camera_motion}")
        if item.recommended_asset_type not in RECOMMENDED_ASSET_TYPES:
            raise ValueError(f"Invalid recommended_asset_type: {item.recommended_asset_type}")
        if item.transition not in TRANSITIONS:
            raise ValueError(f"Invalid transition: {item.transition}")
        if item.bgm_energy not in BGM_ENERGY_LEVELS:
            raise ValueError(f"Invalid bgm_energy: {item.bgm_energy}")
