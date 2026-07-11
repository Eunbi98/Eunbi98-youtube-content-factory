from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass(frozen=True)
class FactoryPaths:
    root_dir: Path
    episode_id: str
    episode_dir: Path
    source_timeline: Path
    source_assets_dir: Path
    remotion_dir: Path
    public_timeline: Path
    public_assets_dir: Path
    output_path: Path
    log_path: Path

    @classmethod
    def create(
        cls,
        *,
        root_dir: Path,
        episode_id: str,
    ) -> "FactoryPaths":
        episode_dir = (
            root_dir
            / "projects"
            / "episodes"
            / episode_id
        )

        remotion_dir = (
            root_dir
            / "projects"
            / "remotion"
        )

        return cls(
            root_dir=root_dir,
            episode_id=episode_id,
            episode_dir=episode_dir,
            source_timeline=(
                episode_dir
                / "timeline.json"
            ),
            source_assets_dir=(
                episode_dir
                / "assets"
            ),
            remotion_dir=remotion_dir,
            public_timeline=(
                remotion_dir
                / "public"
                / "timeline.json"
            ),
            public_assets_dir=(
                remotion_dir
                / "public"
                / "assets"
                / episode_id
            ),
            output_path=(
                root_dir
                / "projects"
                / "output"
                / f"{episode_id}.mp4"
            ),
            log_path=(
                root_dir
                / "projects"
                / "output"
                / "logs"
                / f"{episode_id}.json"
            ),
        )


@dataclass(frozen=True)
class FactoryRunOptions:
    rebuild_timeline: bool = False
    skip_typecheck: bool = False
    validate_only: bool = False


@dataclass
class FactoryRunContext:
    paths: FactoryPaths
    options: FactoryRunOptions
    timeline: dict[str, Any] | None = None
    timeline_generated: bool = False
    title: str = ""
    scene_count: int = 0
    total_duration: float = 0.0
    fps: int = 0
    width: int = 0
    height: int = 0
    required_assets: tuple[Path, ...] = field(
        default_factory=tuple
    )
    required_asset_count: int = 0
    copied_asset_count: int = 0
    elapsed_seconds: float = 0.0
    status: str = "pending"
    error_message: str | None = None

    def build_log_payload(
        self,
    ) -> dict[str, Any]:
        return {
            "release": "6.2",
            "episodeId": self.paths.episode_id,
            "status": self.status,
            "elapsedSeconds": round(
                self.elapsed_seconds,
                2,
            ),
            "timelineGenerated": (
                self.timeline_generated
            ),
            "timelinePath": str(
                self.paths.source_timeline
            ),
            "sourceAssetsPath": str(
                self.paths.source_assets_dir
            ),
            "publicTimelinePath": str(
                self.paths.public_timeline
            ),
            "publicAssetsPath": str(
                self.paths.public_assets_dir
            ),
            "requiredAssetCount": (
                self.required_asset_count
            ),
            "copiedAssetCount": (
                self.copied_asset_count
            ),
            "sceneCount": self.scene_count,
            "totalDuration": round(
                self.total_duration,
                3,
            ),
            "outputPath": (
                str(self.paths.output_path)
                if self.status == "success"
                else None
            ),
            "options": {
                "rebuildTimeline": (
                    self.options.rebuild_timeline
                ),
                "skipTypecheck": (
                    self.options.skip_typecheck
                ),
                "validateOnly": (
                    self.options.validate_only
                ),
            },
            "error": self.error_message,
        }


@dataclass(frozen=True)
class FactoryRunResult:
    episode_id: str
    status: str
    succeeded: bool
    timeline_generated: bool
    scene_count: int
    total_duration: float
    required_asset_count: int
    copied_asset_count: int
    output_path: Path | None
    log_path: Path
    elapsed_seconds: float
