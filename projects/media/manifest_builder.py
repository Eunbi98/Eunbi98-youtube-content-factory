from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from provider_models import MediaCandidate


class ManifestBuilderError(RuntimeError):
    pass


class ManifestBuilder:
    def __init__(
        self,
        *,
        episode_id: str,
        episode_dir: Path,
    ) -> None:
        self.episode_id = episode_id
        self.episode_dir = (
            episode_dir.resolve()
        )
        self.scenes: list[
            dict[str, Any]
        ] = []

    def add_scene(
        self,
        *,
        scene_id: str,
        query: str,
        candidate: MediaCandidate,
        local_path: Path,
        sha256: str,
    ) -> None:
        relative_path = local_path.resolve().relative_to(
            self.episode_dir
        )

        self.scenes.append(
            {
                "sceneId": scene_id,
                "query": query,
                "localPath": relative_path.as_posix(),
                "sha256": sha256,
                "media": candidate.to_dict(),
            }
        )

    def save(
        self,
        output_path: Path,
    ) -> Path:
        payload = {
            "version": "7.0",
            "episodeId": self.episode_id,
            "sceneCount": len(
                self.scenes
            ),
            "scenes": self.scenes,
        }

        output_path.parent.mkdir(
            parents=True,
            exist_ok=True,
        )

        temporary = output_path.with_suffix(
            ".json.tmp"
        )

        try:
            temporary.write_text(
                json.dumps(
                    payload,
                    ensure_ascii=False,
                    indent=2,
                ) + "\n",
                encoding="utf-8",
            )
            temporary.replace(output_path)
        except OSError as exc:
            if temporary.exists():
                temporary.unlink()

            raise ManifestBuilderError(
                "미디어 Manifest 저장에 실패했습니다.\n"
                f"파일: {output_path}\n"
                f"원인: {exc}"
            ) from exc

        return output_path
