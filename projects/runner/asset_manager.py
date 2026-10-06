from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Any


class AssetValidationError(ValueError):
    """에피소드 미디어 파일이 없거나 잘못됐을 때 발생합니다."""


@dataclass(frozen=True)
class AssetSyncResult:
    source_dir: Path
    destination_dir: Path
    required_count: int
    copied_count: int
    asset_paths: tuple[Path, ...]


def _normalize_media_path(
    raw_src: str,
    episode_id: str,
) -> Path:
    normalized = raw_src.replace("\\", "/").strip()

    prefixes = (
        f"assets/{episode_id}/",
        f"public/assets/{episode_id}/",
        f"/assets/{episode_id}/",
        f"/public/assets/{episode_id}/",
    )

    for prefix in prefixes:
        if normalized.lower().startswith(
            prefix.lower()
        ):
            normalized = normalized[len(prefix):]
            break

    normalized = normalized.lstrip("/")

    if not normalized:
        raise AssetValidationError(
            "비어 있는 media.src가 발견되었습니다."
        )

    relative_path = Path(normalized)

    if relative_path.is_absolute():
        raise AssetValidationError(
            f"절대 경로는 사용할 수 없습니다: {raw_src}"
        )

    if ".." in relative_path.parts:
        raise AssetValidationError(
            f"상위 폴더 경로는 사용할 수 없습니다: {raw_src}"
        )

    return relative_path


def collect_required_assets(
    timeline: dict[str, Any],
    *,
    episode_id: str,
) -> tuple[Path, ...]:
    scenes = timeline.get("scenes", [])

    required_assets: list[Path] = []
    seen_assets: set[str] = set()

    for index, scene in enumerate(
        scenes,
        start=1,
    ):
        if not isinstance(scene, dict):
            continue

        media = scene.get("media")

        if not isinstance(media, dict):
            continue

        media_type = media.get("type")

        if media_type in (
            None,
            "color",
        ):
            continue

        raw_src = media.get("src")

        if not isinstance(raw_src, str):
            raise AssetValidationError(
                f"{index}번째 scene의 media.src가 없습니다."
            )

        relative_path = _normalize_media_path(
            raw_src,
            episode_id,
        )

        key = relative_path.as_posix().lower()

        if key not in seen_assets:
            seen_assets.add(key)
            required_assets.append(
                relative_path
            )

    return tuple(required_assets)


def validate_episode_assets(
    *,
    episode_assets_dir: Path,
    required_assets: tuple[Path, ...],
) -> None:
    if required_assets and not episode_assets_dir.exists():
        raise AssetValidationError(
            "에피소드 assets 폴더가 없습니다: "
            f"{episode_assets_dir}"
        )

    missing_assets: list[Path] = []
    empty_assets: list[Path] = []

    for relative_path in required_assets:
        normalized_path = relative_path

        if (
            normalized_path.parts
            and normalized_path.parts[0].lower()
            in {
                "assets",
                episode_assets_dir.parent.name.lower(),
            }
        ):
            normalized_path = Path(
                *normalized_path.parts[1:]
            )

        source_path = (
            episode_assets_dir
            / normalized_path
        )

        if not source_path.exists():
            missing_assets.append(
                relative_path
            )
            continue

        if not source_path.is_file():
            missing_assets.append(
                relative_path
            )
            continue

        if source_path.stat().st_size == 0:
            empty_assets.append(
                relative_path
            )

    if missing_assets:
        missing_text = "\n".join(
            f"  - {path.as_posix()}"
            for path in missing_assets
        )

        raise AssetValidationError(
            "필수 미디어 파일이 없습니다:\n"
            f"{missing_text}"
        )

    if empty_assets:
        empty_text = "\n".join(
            f"  - {path.as_posix()}"
            for path in empty_assets
        )

        raise AssetValidationError(
            "크기가 0바이트인 미디어 파일이 있습니다:\n"
            f"{empty_text}"
        )


def sync_episode_assets(
    *,
    episode_assets_dir: Path,
    public_assets_dir: Path,
    required_assets: tuple[Path, ...],
) -> AssetSyncResult:
    validate_episode_assets(
        episode_assets_dir=episode_assets_dir,
        required_assets=required_assets,
    )

    if public_assets_dir.exists():
        shutil.rmtree(
            public_assets_dir
        )

    public_assets_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    copied_assets: list[Path] = []

    for relative_path in required_assets:
        normalized_path = relative_path

        if (
            normalized_path.parts
            and normalized_path.parts[0].lower()
            in {
                "assets",
                episode_assets_dir.parent.name.lower(),
            }
        ):
            normalized_path = Path(
                *normalized_path.parts[1:]
            )

        source_path = (
            episode_assets_dir
            / normalized_path
        )

        destination_path = (
            public_assets_dir
            / normalized_path
        )

        destination_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        shutil.copy2(
            source_path,
            destination_path,
        )

        copied_assets.append(
            destination_path
        )

    return AssetSyncResult(
        source_dir=episode_assets_dir,
        destination_dir=public_assets_dir,
        required_count=len(
            required_assets
        ),
        copied_count=len(
            copied_assets
        ),
        asset_paths=tuple(
            copied_assets
        ),
    )
