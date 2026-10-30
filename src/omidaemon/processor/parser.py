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
        - Omi Memory Text format (Memory from ..., Title: ..., Overview: ..., Transcript: ...)
        - Omi / Friend JSON format (segments with speaker and text)
        - Timestamped text: [00:12] Speaker: text
        - Plain transcript text
        Returns (normalized_text, list_of_speakers)
        """
        stripped = raw_content.strip()
        if not stripped:
            return "", []

        # 1. Check for Omi Memory Text Format
        if "Memory from" in stripped and "Transcript:" in stripped:
            return cls._parse_omi_memory_text(stripped)

        # 2. Attempt JSON parsing (Omi / Friend / wearable export)
        if stripped.startswith("{") or stripped.startswith("["):
            try:
                data = json.loads(stripped)
                if isinstance(data, dict):
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
                pass

        return cls._parse_text(raw_content)

    @classmethod
    def _parse_omi_memory_text(cls, text: str) -> Tuple[str, List[str]]:
        """Parse Omi's formatted text memories with Title, Overview, and Transcript sections."""
        # Find Transcript: block
        parts = re.split(r"^Transcript:\s*$", text, flags=re.M)
        metadata_header = parts[0].strip()
        transcript_body = parts[1].strip() if len(parts) > 1 else ""

        speakers: Set[str] = set()
        clean_lines = []

        # Parse speaker lines in the transcript body
        speaker_regex = re.compile(r"^(SPEAKER_\d+|[A-Za-z0-9_\s]{2,25}):\s*(.*)$")
        for line in transcript_body.splitlines():
            s_line = line.strip()
            if not s_line:
                continue
            m = speaker_regex.match(s_line)
            if m:
                spk = m.group(1).strip()
                dialogue = m.group(2).strip()
                speakers.add(spk)
                clean_lines.append(f"{spk}: {dialogue}")
            else:
                clean_lines.append(s_line)

        # Include metadata overview context for the LLM
        combined = f"{metadata_header}\n\nTranscript Dialogue:\n" + "\n".join(clean_lines)
        return combined, sorted(list(speakers))

    @classmethod
    def _parse_text(cls, text: str) -> Tuple[str, List[str]]:
        lines = []
        speakers: Set[str] = set()

        # Ignore common metadata headers from being treated as speakers
        reserved_keys = {"title", "overview", "transcript", "memory", "summary", "date", "time"}
        speaker_regex = re.compile(r"^(?:\[[\d:]+\]\s*)?([A-Za-z0-9_\s]{2,30}):\s*(.*)$")

        for raw_line in text.splitlines():
            line = raw_line.strip()
            if not line:
                continue

            match = speaker_regex.match(line)
            if match:
                spk = match.group(1).strip()
                if spk.lower() in reserved_keys:
                    lines.append(line)
                    continue

                dialogue = match.group(2).strip()
                speakers.add(spk)
                lines.append(f"{spk}: {dialogue}")
            else:
                lines.append(line)

        return "\n".join(lines), sorted(list(speakers))

    @staticmethod
    def estimate_word_count(text: str) -> int:
        return len(text.split())
