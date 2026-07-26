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

OUTPUT_DIR = ROOT / "projects" / "output"


def remove_path(path: Path) -> None:
    if path.is_dir():
        shutil.rmtree(path)
        print(f"[폴더 삭제] {path}")

    elif path.is_file():
        path.unlink()
        print(f"[파일 삭제] {path}")


def clear_episode_media() -> None:
    if ASSETS_DIR.exists():
        remove_path(ASSETS_DIR)

    cache_names = {
        "media_manifest.json",
        "timeline.json.media.json",
        "media.json",
        "assets_manifest.json",
        "render_result.json",
    }

    for name in cache_names:
        path = EPISODE_DIR / name

        if path.exists():
            remove_path(path)

    for folder_name in (
        "render",
        "output",
    ):
        path = EPISODE_DIR / folder_name

        if path.exists():
            remove_path(path)


def clear_remotion_public() -> None:
    if not PUBLIC_DIR.exists():
        return

    scene_patterns = (
        "scene_*.jpg",
        "scene_*.jpeg",
        "scene_*.png",
        "scene_*.webp",
    )

    for pattern in scene_patterns:
        for path in PUBLIC_DIR.glob(pattern):
            remove_path(path)

    removable_files = (
        "timeline.json",
        "media_manifest.json",
        "story.json",
        "metadata.json",
    )

    for name in removable_files:
        path = PUBLIC_DIR / name

        if path.exists():
            remove_path(path)


def clear_old_renders() -> None:
    candidates = [
        OUTPUT_DIR / "ep026.mp4",
        REMOTION_DIR / "output" / "ep026.mp4",
        ROOT / "output" / "ep026.mp4",
    ]

    for path in candidates:
        if path.exists():
            remove_path(path)

    for base in (
        OUTPUT_DIR,
        REMOTION_DIR / "output",
        ROOT / "output",
    ):
        if not base.exists():
            continue

        for path in base.glob("*ep026*.mp4"):
            remove_path(path)


def patch_title_style() -> None:
    if not SRC_DIR.exists():
        print("[경고] Remotion src 폴더를 찾지 못했습니다.")
        return

    candidates: list[Path] = []

    for path in SRC_DIR.rglob("*"):
        if path.suffix.lower() not in {".tsx", ".ts", ".jsx", ".js"}:
            continue

        lowered = path.name.lower()

        if (
            "title" in lowered
            or "theme" in lowered
            or "headline" in lowered
        ):
            candidates.append(path)

    changed_files: list[Path] = []

    for path in candidates:
        original = path.read_text(
            encoding="utf-8-sig",
        )

        text = original

        # 제목 두께를 브라우저가 지원하는 최대 굵기로 고정합니다.
        text = re.sub(
            r"(fontWeight\s*:\s*)(?:['\"]?\d+['\"]?|['\"](?:bold|bolder)['\"])",
            r"\g<1>900",
            text,
        )

        # TitleLayer처럼 실제 제목을 렌더하는 파일에만 외곽선을 추가합니다.
        name_lower = path.name.lower()

        if (
            "titlelayer" in name_lower
            or "title" == path.stem.lower()
            or "headline" in name_lower
        ):
            if "WebkitTextStroke" not in text:
                marker_patterns = [
                    r"(fontWeight\s*:\s*900\s*,)",
                    r"(fontWeight\s*:\s*ep005Theme\.title\.fontWeight\s*,)",
                    r"(fontWeight\s*:\s*\w+Theme\.title\.fontWeight\s*,)",
                ]

                inserted = False

                for marker in marker_patterns:
                    if re.search(marker, text):
                        text = re.sub(
                            marker,
                            (
                                r"\1\n"
                                "\t\t\t\tWebkitTextStroke: '2px rgba(0, 0, 0, 0.92)',\n"
                                "\t\t\t\tpaintOrder: 'stroke fill',"
                            ),
                            text,
                            count=1,
                        )
                        inserted = True
                        break

                if not inserted:
                    continue

            # 기존 그림자가 있으면 더 선명하게 교체합니다.
            if re.search(r"textShadow\s*:", text):
                text = re.sub(
                    r"textShadow\s*:\s*[^,\n}]+",
                    (
                        "textShadow: "
                        "'0 4px 0 rgba(0,0,0,0.95), "
                        "0 7px 14px rgba(0,0,0,0.85)'"
                    ),
                    text,
                    count=1,
                )
            else:
                stroke_marker = "paintOrder: 'stroke fill',"

                if stroke_marker in text:
                    text = text.replace(
                        stroke_marker,
                        (
                            stroke_marker
                            + "\n"
                            + "\t\t\t\ttextShadow: "
                            + "'0 4px 0 rgba(0,0,0,0.95), "
                            + "0 7px 14px rgba(0,0,0,0.85)',"
                        ),
                        1,
                    )

        if text != original:
            backup = path.with_suffix(
                path.suffix + ".ep026.bak"
            )

            if not backup.exists():
                shutil.copy2(path, backup)

            path.write_text(
                text,
                encoding="utf-8",
            )

            changed_files.append(path)

    if changed_files:
        for path in changed_files:
            print(f"[제목 스타일 수정] {path}")
    else:
        print(
            "[경고] 자동으로 수정할 제목 파일을 찾지 못했습니다."
        )


def main() -> None:
    if not EPISODE_DIR.exists():
        raise FileNotFoundError(
            f"EP026 폴더가 없습니다: {EPISODE_DIR}"
        )

    print("=" * 64)
    print("EP026 이미지 캐시 완전 초기화")
    print("=" * 64)

    clear_episode_media()
    clear_remotion_public()
    clear_old_renders()
    patch_title_style()

    ASSETS_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    print()
    print("=" * 64)
    print("초기화 완료")
    print("=" * 64)
    print("이제 Factory Runner를 다시 실행하세요.")
    print("기존 이미지와 MP4는 재사용되지 않습니다.")


if __name__ == "__main__":
    main()
