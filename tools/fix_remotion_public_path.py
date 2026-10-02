from __future__ import annotations

import json
import re
import shutil
from pathlib import Path
from typing import Any


ROOT = Path.cwd()

EPISODE_DIR = ROOT / "projects" / "episodes" / "ep026"
ASSETS_DIR = EPISODE_DIR / "assets"

REMOTION_DIR = ROOT / "projects" / "remotion"
SRC_DIR = REMOTION_DIR / "src"
PUBLIC_DIR = REMOTION_DIR / "public"

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def copy_images() -> None:
    PUBLIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for index in range(1, 8):
        scene_id = f"scene_{index:03d}"

        candidates = [
            path
            for path in ASSETS_DIR.rglob("*")
            if (
                path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
                and scene_id in path.stem.lower()
            )
        ]

        if not candidates:
            raise FileNotFoundError(
                f"{scene_id} 이미지가 assets 폴더에 없습니다."
            )

        candidates.sort(
            key=lambda path: (
                path.suffix.lower() != ".jpg",
                len(path.name),
            )
        )

        source = candidates[0]
        destination = PUBLIC_DIR / f"{scene_id}.jpg"

        shutil.copy2(
            source,
            destination,
        )

        print(
            f"[이미지 복사] "
            f"{source.name} -> {destination.name}"
        )


def patch_text_file(path: Path) -> bool:
    original = path.read_text(
        encoding="utf-8-sig",
    )

    updated = original

    replacements = [
        ("/public/scene_", "/scene_"),
        ("public/scene_", "scene_"),
        ("`/public/${", "`/${"),
        ('"/public/${', '"/${'),
        ("'/public/${", "'/${"),
    ]

    for old, new in replacements:
        updated = updated.replace(
            old,
            new,
        )

    # staticFile('/public/scene_001.jpg')
    # → staticFile('scene_001.jpg')
    updated = re.sub(
        r"""staticFile\(\s*(['"`])/public/([^'"`]+)\1\s*\)""",
        r"staticFile(\1\2\1)",
        updated,
    )

    # staticFile('public/scene_001.jpg')
    # → staticFile('scene_001.jpg')
    updated = re.sub(
        r"""staticFile\(\s*(['"`])public/([^'"`]+)\1\s*\)""",
        r"staticFile(\1\2\1)",
        updated,
    )

    if updated == original:
        return False

    backup = path.with_suffix(
        path.suffix + ".public-path.bak"
    )

    if not backup.exists():
        shutil.copy2(
            path,
            backup,
        )

    path.write_text(
        updated,
        encoding="utf-8",
    )

    print(f"[코드 경로 수정] {path}")

    return True


def patch_source_files() -> None:
    changed = 0

    for path in SRC_DIR.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in {".ts", ".tsx", ".js", ".jsx", ".json"}
        ):
            continue

        if patch_text_file(path):
            changed += 1

    print(
        f"[Remotion 코드 수정 파일] {changed}개"
    )


def patch_json_value(value: Any) -> Any:
    if isinstance(value, str):
        value = value.replace(
            "/public/scene_",
            "/scene_",
        )

        value = value.replace(
            "public/scene_",
            "scene_",
        )

        return value

    if isinstance(value, list):
        return [
            patch_json_value(item)
            for item in value
        ]

    if isinstance(value, dict):
        return {
            key: patch_json_value(item)
            for key, item in value.items()
        }

    return value


def patch_json_file(path: Path) -> None:
    if not path.exists():
        return

    with path.open(
        "r",
        encoding="utf-8-sig",
    ) as file:
        data = json.load(file)

    updated = patch_json_value(data)

    with path.open(
        "w",
        encoding="utf-8",
    ) as file:
        json.dump(
            updated,
            file,
            ensure_ascii=False,
            indent=2,
        )

        file.write("\n")

    print(f"[JSON 경로 수정] {path}")


def patch_episode_and_public_json() -> None:
    paths = [
        EPISODE_DIR / "timeline.json",
        EPISODE_DIR / "story.json",
        EPISODE_DIR / "media_manifest.json",
        EPISODE_DIR / "timeline.json.media.json",
        PUBLIC_DIR / "timeline.json",
        PUBLIC_DIR / "story.json",
        PUBLIC_DIR / "media_manifest.json",
    ]

    for path in paths:
        patch_json_file(path)


def copy_timeline() -> None:
    source = EPISODE_DIR / "timeline.json"
    destination = PUBLIC_DIR / "timeline.json"

    if source.exists():
        shutil.copy2(
            source,
            destination,
        )

        print(
            f"[타임라인 복사] "
            f"{source} -> {destination}"
        )


def verify_no_public_scene_path() -> None:
    invalid_files: list[Path] = []

    search_roots = [
        SRC_DIR,
        PUBLIC_DIR,
        EPISODE_DIR,
    ]

    for root in search_roots:
        if not root.exists():
            continue

        for path in root.rglob("*"):
            if (
                not path.is_file()
                or path.suffix.lower()
                not in {
                    ".ts",
                    ".tsx",
                    ".js",
                    ".jsx",
                    ".json",
                }
            ):
                continue

            try:
                text = path.read_text(
                    encoding="utf-8-sig",
                )
            except UnicodeDecodeError:
                continue

            if "/public/scene_" in text:
                invalid_files.append(path)

    if invalid_files:
        print()
        print("[아직 잘못된 경로가 남아 있습니다]")

        for path in invalid_files:
            print(path)

        raise RuntimeError(
            "/public/scene_ 경로 수정이 완료되지 않았습니다."
        )


def verify_images() -> None:
    print()
    print("=" * 64)
    print("Remotion public 이미지 확인")
    print("=" * 64)

    for index in range(1, 8):
        path = (
            PUBLIC_DIR
            / f"scene_{index:03d}.jpg"
        )

        if not path.exists():
            raise FileNotFoundError(
                f"누락 이미지: {path}"
            )

        print(
            f"[확인] {path.name}: "
            f"{path.stat().st_size:,} bytes"
        )


def main() -> None:
    if not ASSETS_DIR.exists():
        raise FileNotFoundError(
            f"assets 폴더가 없습니다: {ASSETS_DIR}"
        )

    copy_images()
    patch_source_files()
    patch_episode_and_public_json()
    copy_timeline()
    verify_no_public_scene_path()
    verify_images()

    print()
    print("=" * 64)
    print("EP026 이미지 경로 수정 완료")
    print("=" * 64)
    print(
        "이제 /public/scene_001.jpg가 아니라 "
        "/scene_001.jpg로 렌더됩니다."
    )


if __name__ == "__main__":
    main()
