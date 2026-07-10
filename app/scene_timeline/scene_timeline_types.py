from __future__ import annotations

from dataclasses import dataclass


CAMERA_MOTIONS = {
    "static",
    "slow_zoom_in",
    "slow_zoom_out",
    "pan_left",
    "pan_right",
    "push_in",
}

RECOMMENDED_ASSET_TYPES = {
    "official_video",
    "official_image",
    "infographic",
    "animation",
}

TRANSITIONS = {
    "cross_dissolve",
    "cut",
    "dip_to_black",
}

BGM_ENERGY_LEVELS = {
    "low",
    "medium",
    "high",
}


@dataclass(frozen=True)
class SceneTimelineItem:
    scene_id: str
    duration: float
    start_time: float
    end_time: float
    purpose: str
    narration: str
    caption: str
    recommended_asset_type: str
    camera_motion: str
    transition: str
    sfx: str
    bgm_energy: str

    def to_dict(self) -> dict[str, object]:
        return {
            "scene_id": self.scene_id,
            "duration": self.duration,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "purpose": self.purpose,
            "narration": self.narration,
            "caption": self.caption,
            "recommended_asset_type": self.recommended_asset_type,
            "camera_motion": self.camera_motion,
            "transition": self.transition,
            "sfx": self.sfx,
            "bgm_energy": self.bgm_energy,
        }
