from __future__ import annotations

import shutil
import subprocess
from pathlib import Path
from typing import Sequence


class CommandExecutionError(RuntimeError):
    """외부 명령 실행 실패."""


def find_windows_command(
    command: str,
) -> str:
    candidates = (
        f"{command}.cmd",
        f"{command}.exe",
        command,
    )

    for candidate in candidates:
        resolved = shutil.which(candidate)
        if resolved:
            return resolved

    raise CommandExecutionError(
        f"명령을 찾을 수 없습니다: {command}"
    )


def run_command(
    command: Sequence[str],
    *,
    cwd: Path,
    step_name: str,
) -> None:
    print()
    print(f"[실행] {step_name}")
    print("       " + " ".join(command))

    process = subprocess.run(
        list(command),
        cwd=cwd,
        check=False,
        text=True,
        encoding="utf-8",
        errors="replace",
    )

    if process.returncode != 0:
        raise CommandExecutionError(
            f"{step_name} 실패 "
            f"(종료 코드: {process.returncode})"
        )

    print(f"[완료] {step_name}")


def typecheck_remotion(
    remotion_dir: Path,
) -> None:
    npx = find_windows_command("npx")

    run_command(
        [
            npx,
            "tsc",
            "--noEmit",
        ],
        cwd=remotion_dir,
        step_name="TypeScript 검사",
    )


def render_episode(
    remotion_dir: Path,
    output_path: Path,
) -> None:
    npx = find_windows_command("npx")

    output_path.parent.mkdir(
        parents=True,
        exist_ok=True,
    )

    run_command(
        [
            npx,
            "remotion",
            "render",
            "src/index.ts",
            "Episode",
            str(output_path.resolve()),
        ],
        cwd=remotion_dir,
        step_name="Remotion 렌더",
    )

    if not output_path.exists():
        raise CommandExecutionError(
            "렌더 명령은 완료됐지만 MP4가 생성되지 않았습니다: "
            f"{output_path}"
        )
