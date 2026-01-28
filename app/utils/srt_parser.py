"""SRT subtitle parsing utilities for extracting transcripts from global SRT content."""

import re
from dataclasses import dataclass


@dataclass
class SrtCue:
    """Represents a single SRT subtitle cue."""

    index: int
    start: float  # seconds
    end: float  # seconds
    speaker: str | None  # e.g., "Speaker 1" or None
    text: str  # raw text without speaker tag


def _parse_timestamp(ts: str) -> float:
    """
    Parse SRT timestamp to seconds.

    Args:
        ts: Timestamp in format "HH:MM:SS,mmm" or "HH:MM:SS.mmm"

    Returns:
        Time in seconds as float
    """
    # Handle both comma and period as decimal separator
    ts = ts.replace(",", ".")
    parts = ts.split(":")

    if len(parts) != 3:
        return 0.0

    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except (ValueError, IndexError):
        return 0.0


def _extract_speaker_and_text(text: str) -> tuple[str | None, str]:
    """
    Extract speaker tag and clean text from SRT cue text.

    Args:
        text: Raw text that may contain speaker tags like "[Speaker 1]: "

    Returns:
        Tuple of (speaker, clean_text)
    """
    # Pattern matches [Speaker X]: or [Speaker Name]:
    speaker_pattern = r"^\[([^\]]+)\]:\s*"
    match = re.match(speaker_pattern, text)

    if match:
        speaker = match.group(1)
        clean_text = text[match.end() :].strip()
        return speaker, clean_text

    return None, text.strip()


def parse_srt(srt_content: str) -> list[SrtCue]:
    """
    Parse SRT content into a list of SrtCue objects.

    Args:
        srt_content: Full SRT file content as string

    Returns:
        List of SrtCue objects, sorted by start time
    """
    if not srt_content:
        return []

    cues: list[SrtCue] = []

    # Split into blocks (separated by blank lines)
    blocks = re.split(r"\n\s*\n", srt_content.strip())

    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 3:
            continue

        try:
            # First line is index
            index = int(lines[0].strip())

            # Second line is timestamp range
            timestamp_line = lines[1].strip()
            timestamp_match = re.match(
                r"(\d{2}:\d{2}:\d{2}[,\.]\d{3})\s*-->\s*(\d{2}:\d{2}:\d{2}[,\.]\d{3})",
                timestamp_line,
            )
            if not timestamp_match:
                continue

            start = _parse_timestamp(timestamp_match.group(1))
            end = _parse_timestamp(timestamp_match.group(2))

            # Remaining lines are text (may span multiple lines)
            raw_text = " ".join(lines[2:]).strip()
            speaker, text = _extract_speaker_and_text(raw_text)

            cues.append(
                SrtCue(
                    index=index,
                    start=start,
                    end=end,
                    speaker=speaker,
                    text=text,
                )
            )
        except (ValueError, IndexError):
            # Skip malformed blocks
            continue

    # Sort by start time
    return sorted(cues, key=lambda c: c.start)


def get_cues_for_range(
    cues: list[SrtCue],
    start: float,
    end: float,
) -> list[SrtCue]:
    """
    Get all SRT cues that overlap with a time range.

    A cue overlaps if any part of it falls within the range.

    Args:
        cues: List of parsed SRT cues
        start: Range start time in seconds
        end: Range end time in seconds

    Returns:
        List of overlapping cues, sorted by start time
    """
    overlapping = []
    for cue in cues:
        # Check if cue overlaps with range
        # Overlaps if cue starts before range ends AND cue ends after range starts
        if cue.start < end and cue.end > start:
            overlapping.append(cue)

    return sorted(overlapping, key=lambda c: c.start)


def get_transcript_for_range(
    cues: list[SrtCue],
    start: float,
    end: float,
) -> str:
    """
    Get combined transcript text for a time range (speaker tags stripped).

    Args:
        cues: List of parsed SRT cues
        start: Range start time in seconds
        end: Range end time in seconds

    Returns:
        Combined transcript text with speaker tags removed
    """
    overlapping = get_cues_for_range(cues, start, end)

    if not overlapping:
        return ""

    # Combine text from all overlapping cues
    texts = [cue.text for cue in overlapping if cue.text]
    return " ".join(texts)


def get_dominant_speaker(
    cues: list[SrtCue],
    start: float,
    end: float,
) -> str | None:
    """
    Get the most frequent speaker in a time range.

    Calculates based on the amount of time each speaker speaks within the range.

    Args:
        cues: List of parsed SRT cues
        start: Range start time in seconds
        end: Range end time in seconds

    Returns:
        The speaker label with the most speaking time, or None if no speakers found
    """
    overlapping = get_cues_for_range(cues, start, end)

    if not overlapping:
        return None

    # Calculate speaking time per speaker
    speaker_times: dict[str, float] = {}

    for cue in overlapping:
        if cue.speaker is None:
            continue

        # Calculate how much of this cue falls within the range
        cue_start = max(cue.start, start)
        cue_end = min(cue.end, end)
        duration = max(0, cue_end - cue_start)

        speaker_times[cue.speaker] = speaker_times.get(cue.speaker, 0) + duration

    if not speaker_times:
        return None

    # Return speaker with most time
    return max(speaker_times, key=speaker_times.get)  # type: ignore[arg-type]
