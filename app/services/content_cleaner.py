class ContentCleaner:

    REMOVE_KEYWORDS = [
        "Sign up",
        "Subscribe",
        "Read more",
        "Follow us",
        "Share this",
        "Related Topics",
        "More on this story",
        "Copyright",
        "All rights reserved",
        "Advertisement",
        "This video can not be played",
        "Please enable JavaScript",
    ]

    def clean(self, content: str) -> str:
        if not content:
            return ""

        lines = content.splitlines()

        cleaned_lines = []

        for line in lines:
            line = line.strip()

            if not line:
                continue

            if len(line) < 20:
                continue

            if self._should_remove(line):
                continue

            cleaned_lines.append(line)

        return "\n".join(cleaned_lines)

    def _should_remove(self, line: str) -> bool:
        lower_line = line.lower()

        for keyword in self.REMOVE_KEYWORDS:
            if keyword.lower() in lower_line:
                return True

        return False