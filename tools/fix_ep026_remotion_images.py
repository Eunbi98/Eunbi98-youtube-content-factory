from __future__ import annotations

import re
import shutil
from pathlib import Path


ROOT = Path.cwd()

EPISODE_DIR = ROOT / "projects" / "episodes" / "ep026"
ASSETS_DIR = EPISODE_DIR / "assets"

REMOTION_DIR = ROOT / "projects" / "remotion"
PUBLIC_DIR = REMOTION_DIR / "public"
SRC_DIR = REMOTION_DIR / "src"

IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".webp",
}


def find_scene_image(scene_id: str) -> Path | None:
    candidates: list[Path] = []

    if ASSETS_DIR.exists():
        for path in ASSETS_DIR.rglob("*"):
            if (
                path.is_file()
                and path.suffix.lower() in IMAGE_EXTENSIONS
                and scene_id.lower() in path.stem.lower()
            ):
                candidates.append(path)

    if not candidates:
        return None

    candidates.sort(
        key=lambda path: (
            path.suffix.lower() != ".jpg",
            len(path.name),
        )
    )

    return candidates[0]


def copy_scene_images() -> None:
    PUBLIC_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    for old_image in PUBLIC_DIR.glob("scene_*"):
        if (
            old_image.is_file()
            and old_image.suffix.lower() in IMAGE_EXTENSIONS
        ):
            old_image.unlink()
            print(f"[기존 public 이미지 삭제] {old_image.name}")

    missing: list[str] = []

    for index in range(1, 8):
        scene_id = f"scene_{index:03d}"
        source = find_scene_image(scene_id)

        if source is None:
            missing.append(scene_id)
            continue

        destination = PUBLIC_DIR / f"{scene_id}.jpg"

        shutil.copy2(
            source,
            destination,
        )

        print(
            f"[복사] {source.name}"
            f" -> {destination.name}"
        )

    if missing:
        raise FileNotFoundError(
            "다음 장면 이미지가 assets 폴더에 없습니다: "
            + ", ".join(missing)
        )


def patch_remotion_paths() -> None:
    changed_files: list[Path] = []

    for path in SRC_DIR.rglob("*"):
        if (
            not path.is_file()
            or path.suffix.lower()
            not in {".ts", ".tsx", ".js", ".jsx"}
        ):
            continue

        original = path.read_text(
            encoding="utf-8-sig",
        )

        updated = original

        # "/public/scene_001.jpg" → "/scene_001.jpg"
        updated = re.sub(
            r"""(['"`])/?public/(scene_[^'"`]+?\.(?:jpg|jpeg|png|webp))\1""",
            r"\1/\2\1",
            updated,
            flags=re.IGNORECASE,
        )

        # `public/${...}` → `${...}`
        updated = re.sub(
            r"""(['"`])/?public/\$\{""",
            r"\1/${",
            updated,
            flags=re.IGNORECASE,
        )

        # public/scene 경로 문자열 보정
        updated = updated.replace(
            "/public/scene_",
            "/scene_",
        )

        updated = updated.replace(
            "public/scene_",
            "scene_",
        )

        if updated != original:
            backup = path.with_suffix(
                path.suffix + ".pathfix.bak"
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

            changed_files.append(path)

    if changed_files:
        for path in changed_files:
            print(f"[경로 수정] {path}")
    else:
        print(
            "[안내] 코드에서 직접적인 /public/scene 경로는 "
            "발견되지 않았습니다."
        )


def verify() -> None:
    missing: list[str] = []

    for index in range(1, 8):
        filename = f"scene_{index:03d}.jpg"
        path = PUBLIC_DIR / filename

        if not path.exists():
            missing.append(filename)

    if missing:
        raise FileNotFoundError(
            "Remotion public 이미지 누락: "
            + ", ".join(missing)
        )

    print()
    print("=" * 64)
    print("EP026 Remotion 이미지 경로 수정 완료")
    print("=" * 64)

    for index in range(1, 8):
        path = PUBLIC_DIR / f"scene_{index:03d}.jpg"

        print(
            f"[확인] {path.name}: "
            f"{path.stat().st_size:,} bytes"
        )


def main() -> None:
    if not ASSETS_DIR.exists():
        raise FileNotFoundError(
            f"EP026 assets 폴더가 없습니다: {ASSETS_DIR}"
        )

    copy_scene_images()
    patch_remotion_paths()
    verify()


if __name__ == "__main__":
    main()
