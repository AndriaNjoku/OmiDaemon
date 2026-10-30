"""Parser and preprocessor for raw wearable audio transcripts."""

import json
import re
from typing import List, Tuple, Set


class TranscriptParser:
    @classmethod
    def parse(cls, raw_content: str) -> Tuple[str, List[str]]:
        """
        Parses raw transcript content into normalized readable dialogue.
        Supports:
        - Omi / Friend JSON format (segments with speaker and text)
        - Timestamped text: [00:12] Speaker: text
        - Plain transcript text
        Returns (normalized_text, list_of_speakers)
        """
        stripped = raw_content.strip()
        if not stripped:
            return "", []

        # 1. Attempt JSON parsing (Omi / Friend / wearable export)
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict):
                    # Omi schema often has 'segments' or 'transcript' or 'structured'
                    if "segments" in data and isinstance(data["segments"], list):
                        lines = []
                        speakers: Set[str] = set()
                        for seg in data["segments"]:
                            spk = seg.get("speaker") or seg.get("speaker_id") or "Speaker"
                            text = seg.get("text", "").strip()
                            if text:
                                speakers.add(str(spk))
                                lines.append(f"{spk}: {text}")
                        if lines:
                            return "\n".join(lines), sorted(list(speakers))

                    if "transcript" in data and isinstance(data["transcript"], str):
                        return cls._parse_text(data["transcript"])

                elif isinstance(data, list):
                    lines = []
                    speakers = set()
                    for item in data:
                        if isinstance(item, dict):
                            spk = item.get("speaker") or "Speaker"
                            text = item.get("text", "").strip()
                            if text:
                                speakers.add(str(spk))
                                lines.append(f"{spk}: {text}")
                    if lines:
                        return "\n".join(lines), sorted(list(speakers))
            except Exception:
                pass  # Fall back to plain text parsing

        return cls._parse_text(raw_content)

    @classmethod
    def _parse_text(cls, text: str) -> Tuple[str, List[str]]:
        lines = []
        speakers: Set[str] = set()

        # Regex for speaker prefixes e.g. "Speaker 1:", "[00:12] Speaker 0:", "John Doe:"
        speaker_regex = re.compile(r"^(?:\[[\d:]+\]\s*)?([A-Za-z0-9_\s]{2,30}):\s*(.*)$")

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            match = speaker_regex.match(line)
            if match:
                spk = match.group(1).strip()
                dialogue = match.group(2).strip()
                speakers.add(spk)
                lines.append(f"{spk}: {dialogue}")
            else:
                lines.append(line)

        return "\n".join(lines), sorted(list(speakers))

    @staticmethod
    def estimate_word_count(text: str) -> int:
        return len(text.split())
