from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any


class AssetDedupReporter:
    def generate_from_files(
        self,
        sources_path: Path | str,
        download_report_path: Path | str,
        scene_timeline_path: Path | str,
        output_dir: Path | str | None = None,
    ) -> dict[str, object]:
        sources_file = Path(sources_path)
        scene_timeline_file = Path(scene_timeline_path)
        target_dir = Path(output_dir) if output_dir else sources_file.parent

        sources = self._load_json(sources_file)
        scene_timeline = self._load_json(scene_timeline_file)
        download_report_text = Path(download_report_path).read_text(encoding="utf-8")

        selection = self.generate(sources, scene_timeline, download_report_text)

        target_dir.mkdir(parents=True, exist_ok=True)
        selection_path = target_dir / "asset_selection.json"
        report_path = target_dir / "asset_dedup_report.md"
        selection_path.write_text(
            json.dumps(selection, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        report_path.write_text(
            self._render_report(selection),
            encoding="utf-8",
        )
        return selection

    def generate(
        self,
        sources: dict[str, Any],
        scene_timeline: dict[str, Any],
        download_report_text: str,
    ) -> dict[str, object]:
        assets = [self._enrich_asset(asset) for asset in sources.get("assets", [])]
        groups = self._dedup_groups(assets)
        representative_by_key = {
            key: self._representative(group)
            for key, group in groups.items()
        }
        scenes = scene_timeline.get("scenes", [])
        scene_selections = [
            self._select_scene_asset(scene, assets, representative_by_key)
            for scene in scenes
        ]

        duplicate_groups = [
            self._duplicate_group_record(key, group, representative_by_key[key])
            for key, group in groups.items()
            if len(group) > 1
        ]

        return {
            "episode_id": sources.get("episode_id") or scene_timeline.get("episode_id"),
            "policy": {
                "delete_files": False,
                "dedup_basis": ["download_url", "sha256"],
                "scene_asset_limit": 1,
                "license_policy": "representative_license_only",
            },
            "summary": {
                "downloaded_asset_count": len(assets),
                "unique_asset_count": len(groups),
                "duplicate_group_count": len(duplicate_groups),
                "scene_count": len(scenes),
                "manual_needed_count": sum(1 for item in scene_selections if item["manual_needed"]),
            },
            "representative_assets": [
                self._asset_record(asset)
                for asset in representative_by_key.values()
            ],
            "duplicate_groups": duplicate_groups,
            "scenes": scene_selections,
            "download_report_observed": {
                "has_report": bool(download_report_text.strip()),
                "skipped_mentions": download_report_text.count("No direct downloadable asset could be resolved."),
            },
        }

    def _select_scene_asset(
        self,
        scene: dict[str, Any],
        assets: list[dict[str, Any]],
        representative_by_key: dict[str, dict[str, Any]],
    ) -> dict[str, object]:
        scene_id = str(scene["scene_id"])
        scene_assets = [asset for asset in assets if asset.get("scene") == scene_id]
        recommended_type = str(scene.get("recommended_asset_type", "official_image"))
        preferred_media_type = "video" if recommended_type == "official_video" else "image"

        exact_candidates = [
            asset
            for asset in scene_assets
            if asset.get("media_type") == preferred_media_type
        ]
        fallback_candidates = list(scene_assets)
        chosen = self._choose_best_asset(exact_candidates or fallback_candidates)
        manual_needed = False
        manual_reason = ""

        if not chosen:
            manual_needed = True
            manual_reason = "No downloaded asset exists for this scene."
        elif chosen.get("media_type") != preferred_media_type:
            manual_needed = True
            manual_reason = f"Scene expects {recommended_type}, but only {chosen.get('media_type')} is available."
        elif recommended_type in {"infographic", "animation"}:
            manual_needed = True
            manual_reason = f"Scene expects {recommended_type}; downloaded official media cannot replace generated explanatory visuals."

        representative = None
        if chosen:
            representative = representative_by_key[self._dedup_key(chosen)]

        return {
            "scene_id": scene_id,
            "purpose": scene.get("purpose"),
            "recommended_asset_type": recommended_type,
            "required_media_type": preferred_media_type,
            "selected_asset": self._asset_record(representative) if representative else None,
            "selected_from_scene_asset": self._asset_record(chosen) if chosen else None,
            "uses_representative_asset": bool(chosen and representative and chosen["local_path"] != representative["local_path"]),
            "manual_needed": manual_needed,
            "manual_reason": manual_reason,
            "search_queries": self._gap_queries(scene),
        }

    def _choose_best_asset(self, candidates: list[dict[str, Any]]) -> dict[str, Any] | None:
        if not candidates:
            return None
        return sorted(
            candidates,
            key=lambda asset: (
                -int(asset.get("trust_score", 0)),
                0 if asset.get("source") == "NOAA" else 1,
                str(asset.get("local_path", "")),
            ),
        )[0]

    def _dedup_groups(self, assets: list[dict[str, Any]]) -> dict[str, list[dict[str, Any]]]:
        groups: dict[str, list[dict[str, Any]]] = {}
        for asset in assets:
            key = self._dedup_key(asset)
            groups.setdefault(key, []).append(asset)
        return groups

    def _dedup_key(self, asset: dict[str, Any]) -> str:
        download_url = str(asset.get("download_url") or "")
        if download_url:
            return f"url:{download_url}"
        return f"sha256:{asset.get('sha256', '')}"

    def _representative(self, group: list[dict[str, Any]]) -> dict[str, Any]:
        return sorted(
            group,
            key=lambda asset: (
                str(asset.get("scene", "")),
                0 if asset.get("source") == "NOAA" else 1,
                str(asset.get("local_path", "")),
            ),
        )[0]

    def _duplicate_group_record(
        self,
        key: str,
        group: list[dict[str, Any]],
        representative: dict[str, Any],
    ) -> dict[str, object]:
        return {
            "dedup_key": key,
            "duplicate_count": len(group),
            "representative_asset": self._asset_record(representative),
            "duplicate_assets": [
                self._asset_record(asset)
                for asset in group
                if asset["local_path"] != representative["local_path"]
            ],
            "duplicate_license_paths": [
                asset.get("license_path")
                for asset in group
                if asset["local_path"] != representative["local_path"]
            ],
        }

    def _asset_record(self, asset: dict[str, Any] | None) -> dict[str, object] | None:
        if not asset:
            return None
        return {
            "scene": asset.get("scene"),
            "title": asset.get("title"),
            "source": asset.get("source"),
            "media_type": asset.get("media_type"),
            "local_path": asset.get("local_path"),
            "download_url": asset.get("download_url"),
            "license": asset.get("license"),
            "license_path": asset.get("license_path"),
            "trust_score": asset.get("trust_score"),
            "sha256": asset.get("sha256"),
            "bytes": asset.get("bytes"),
        }

    def _enrich_asset(self, asset: dict[str, Any]) -> dict[str, Any]:
        enriched = dict(asset)
        local_path = Path(str(asset.get("local_path", "")))
        if local_path.exists():
            enriched["sha256"] = self._sha256(local_path)
        else:
            enriched["sha256"] = ""
        return enriched

    def _sha256(self, path: Path) -> str:
        hasher = hashlib.sha256()
        with path.open("rb") as file:
            for chunk in iter(lambda: file.read(1024 * 1024), b""):
                hasher.update(chunk)
        return hasher.hexdigest()

    def _gap_queries(self, scene: dict[str, Any]) -> list[str]:
        scene_id = str(scene.get("scene_id", ""))
        purpose = str(scene.get("purpose", "")).lower()
        recommended_type = str(scene.get("recommended_asset_type", ""))

        if scene_id == "scene_01":
            return [
                "Mariana Trench submersible footage",
                "NOAA Mariana Trench descent video",
                "Challenger Deep official footage",
            ]
        if "pressure" in purpose or recommended_type == "infographic":
            return [
                "NOAA deep sea pressure",
                "Challenger Deep animation",
                "Mariana Trench pressure infographic",
            ]
        if "submersible" in purpose:
            return [
                "Mariana Trench submersible footage",
                "bathyscaphe Trieste Mariana Trench",
                "Limiting Factor submersible deep sea",
            ]
        if "wonder" in purpose:
            return [
                "deep sea creatures NOAA",
                "NOAA hydrothermal vent deep sea life",
                "Mariana Trench deep sea creatures footage",
            ]
        if "ending" in purpose:
            return [
                "Challenger Deep bathymetry map",
                "NOAA Mariana Trench map",
                "deep ocean floor map NOAA",
            ]
        if recommended_type == "animation":
            return [
                "Challenger Deep animation",
                "deep sea pressure animation",
                "Mariana Trench depth animation",
            ]
        return [
            "NOAA deep sea pressure",
            "Mariana Trench submersible footage",
            "deep sea creatures NOAA",
        ]

    def _render_report(self, selection: dict[str, object]) -> str:
        summary = selection["summary"]
        lines = [
            "# EP002 Asset Dedup & Gap Report",
            "",
            f"- Downloaded assets: {summary['downloaded_asset_count']}",
            f"- Unique representative assets: {summary['unique_asset_count']}",
            f"- Duplicate groups: {summary['duplicate_group_count']}",
            f"- Scenes: {summary['scene_count']}",
            f"- Manual-needed scenes: {summary['manual_needed_count']}",
            "- Actual files deleted: no",
            "",
            "## Scene Selection",
            "",
        ]

        for scene in selection["scenes"]:
            selected = scene.get("selected_asset") or {}
            lines.extend(
                [
                    f"### {scene['scene_id']} - {scene['purpose']}",
                    f"- Recommended asset type: {scene['recommended_asset_type']}",
                    f"- Selected: {selected.get('media_type', 'none')} / {selected.get('source', 'none')}",
                    f"- Representative file: `{selected.get('local_path', '')}`",
                    f"- Manual needed: {str(scene['manual_needed']).lower()}",
                    f"- Reason: {scene['manual_reason'] or 'Downloaded representative asset is usable.'}",
                    "- Search queries:",
                ]
            )
            for query in scene["search_queries"]:
                lines.append(f"  - {query}")
            lines.append("")

        lines.extend(["## Duplicate Groups", ""])
        for group in selection["duplicate_groups"]:
            representative = group["representative_asset"]
            lines.extend(
                [
                    f"### {representative['title']}",
                    f"- Dedup key: `{group['dedup_key']}`",
                    f"- Duplicate count: {group['duplicate_count']}",
                    f"- Keep representative: `{representative['local_path']}`",
                    f"- Keep license: `{representative['license_path']}`",
                    "- Duplicate files to ignore:",
                ]
            )
            for duplicate in group["duplicate_assets"]:
                lines.append(f"  - `{duplicate['local_path']}`")
            lines.append("- Duplicate licenses to ignore:")
            for license_path in group["duplicate_license_paths"]:
                lines.append(f"  - `{license_path}`")
            lines.append("")

        lines.extend(
            [
                "## Notes",
                "",
                "- This report does not delete or move any files.",
                "- Duplicate assets should be ignored by future render/selection steps unless a scene explicitly needs a separate copy.",
                "- License dedup keeps only the representative license path in asset_selection.json.",
                "",
            ]
        )
        return "\n".join(lines)

    def _load_json(self, path: Path) -> dict[str, Any]:
        data = json.loads(path.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            raise ValueError(f"{path} must contain a JSON object.")
        return data
