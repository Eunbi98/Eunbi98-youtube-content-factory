from __future__ import annotations

import argparse
import json
import shutil
from pathlib import Path
from typing import Any


class SceneMediaRecoveryError(RuntimeError):
    pass


def _read_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(payload, dict):
        raise SceneMediaRecoveryError("Timeline 최상위 값은 객체여야 합니다.")
    return payload


def _resolve_media_path(assets_dir: Path, raw_src: str) -> Path:
    src = raw_src.strip().lstrip("/\\")
    path = Path(src)
    if path.parts and path.parts[0].lower() in {"assets", assets_dir.parent.name.lower()}:
        path = Path(*path.parts[1:])
    return assets_dir / path


def _valid_scene_media(scene: dict[str, Any], assets_dir: Path) -> Path | None:
    media = scene.get("media")
    if not isinstance(media, dict) or media.get("type") not in {"image", "video"}:
        return None
    src = media.get("src")
    if not isinstance(src, str) or not src.strip():
        return None
    path = _resolve_media_path(assets_dir, src)
    if path.is_file() and path.stat().st_size > 0:
        return path
    return None


def recover_missing_scene_media(*, timeline_path: Path, assets_dir: Path) -> list[str]:
    timeline = _read_json(timeline_path)
    scenes = timeline.get("scenes")
    if not isinstance(scenes, list):
        raise SceneMediaRecoveryError("Timeline scenes가 배열이 아닙니다.")

    valid: list[tuple[int, Path]] = []
    missing: list[int] = []
    for index, scene in enumerate(scenes):
        if not isinstance(scene, dict):
            continue
        media_path = _valid_scene_media(scene, assets_dir)
        if media_path is None:
            missing.append(index)
        else:
            valid.append((index, media_path))

    if not missing:
        return []
    if not valid:
        raise SceneMediaRecoveryError("재사용할 수 있는 기존 Scene 미디어가 없습니다.")

    recovered: list[str] = []
    assets_dir.mkdir(parents=True, exist_ok=True)
    for index in missing:
        scene = scenes[index]
        if not isinstance(scene, dict):
            continue
        scene_id = str(scene.get("id") or f"scene_{index + 1:03d}")
        _, source = min(valid, key=lambda item: abs(item[0] - index))
        extension = source.suffix.lower() or ".jpg"
        destination = assets_dir / f"{scene_id}_fallback{extension}"
        shutil.copy2(source, destination)
        scene["media"] = {
            "type": "video" if extension in {".mp4", ".mov", ".webm"} else "image",
            "src": f"assets/{destination.name}",
            "fit": "cover",
            "fallback": True,
            "fallbackSource": source.name,
        }
        recovered.append(scene_id)

    timeline_path.write_text(
        json.dumps(timeline, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return recovered


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="누락 Scene에 인접 장면 미디어를 재사용합니다.")
    parser.add_argument("--timeline", type=Path, required=True)
    parser.add_argument("--assets", type=Path, required=True)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        recovered = recover_missing_scene_media(
            timeline_path=args.timeline,
            assets_dir=args.assets,
        )
    except (OSError, json.JSONDecodeError, SceneMediaRecoveryError) as exc:
        print(f"[복구 실패] {exc}")
        return 1
    if recovered:
        print("복구된 Scene: " + ", ".join(recovered))
    else:
        print("복구할 Scene이 없습니다.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
