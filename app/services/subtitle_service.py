from pathlib import Path


class SubtitleService:

    def __init__(self):
        self.output_dir = Path("output/subtitles")
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def create_srt(self, article) -> str | None:
        if not article.script:
            return None

        lines = self._split_script(article.script)

        if not lines:
            return None

        filename = "news.srt"
        output_path = self.output_dir / filename

        with open(output_path, "w", encoding="utf-8") as f:
            for index, line in enumerate(lines, start=1):
                start_seconds = (index - 1) * 4
                end_seconds = index * 4

                f.write(f"{index}\n")
                f.write(
                    f"{self._format_time(start_seconds)} --> "
                    f"{self._format_time(end_seconds)}\n"
                )
                f.write(f"{line}\n\n")

        return str(output_path)

    def _split_script(self, script: str) -> list[str]:
        lines = []

        for line in script.splitlines():
            line = line.strip()

            if not line:
                continue

            if line.startswith("-"):
                line = line[1:].strip()

            lines.append(line)

        return lines

    def _format_time(self, seconds: int) -> str:
        hours = seconds // 3600
        minutes = (seconds % 3600) // 60
        secs = seconds % 60

        return f"{hours:02}:{minutes:02}:{secs:02},000"