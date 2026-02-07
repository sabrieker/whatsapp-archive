import re
from dataclasses import dataclass
from datetime import datetime
from typing import Iterator, Optional
import logging

logger = logging.getLogger(__name__)

# Unicode characters to strip (invisible formatting characters)
UNICODE_STRIP_CHARS = '\u200e\u200f\u202a\u202b\u202c\u202d\u202e\u2066\u2067\u2068\u2069\ufeff'


def clean_unicode(text: str) -> str:
    """Remove invisible Unicode formatting characters."""
    for char in UNICODE_STRIP_CHARS:
        text = text.replace(char, '')
    return text


@dataclass
class ParsedMessage:
    timestamp: datetime
    sender: str
    content: str
    message_type: str = "text"
    has_media: bool = False
    media_filename: Optional[str] = None
    is_system: bool = False


class WhatsAppParser:
    """Parser for WhatsApp chat export files."""

    # Multiple date formats WhatsApp uses
    DATE_PATTERNS = [
        # DD.MM.YYYY, HH:MM:SS (European with seconds)
        (r"\[(\d{2})\.(\d{2})\.(\d{4}),\s*(\d{2}):(\d{2}):(\d{2})\]", "%d.%m.%Y %H:%M:%S"),
        # DD/MM/YYYY, HH:MM:SS (European with slashes)
        (r"\[(\d{2})/(\d{2})/(\d{4}),\s*(\d{2}):(\d{2}):(\d{2})\]", "%d/%m/%Y %H:%M:%S"),
        # MM/DD/YY, HH:MM:SS (US format)
        (r"\[(\d{1,2})/(\d{1,2})/(\d{2}),\s*(\d{1,2}):(\d{2}):(\d{2})\s*(AM|PM)?\]", "us_format"),
        # DD.MM.YYYY, HH:MM (European without seconds)
        (r"\[(\d{2})\.(\d{2})\.(\d{4}),\s*(\d{2}):(\d{2})\]", "%d.%m.%Y %H:%M"),
        # DD/MM/YYYY, HH:MM (European with slashes, no seconds)
        (r"\[(\d{2})/(\d{2})/(\d{4}),\s*(\d{2}):(\d{2})\]", "%d/%m/%Y %H:%M"),
    ]

    # Message line pattern: [timestamp] sender: message
    MESSAGE_PATTERN = re.compile(r"^\[([^\]]+)\]\s*([^:]+):\s*(.*)$")

    # System message pattern (no sender)
    SYSTEM_PATTERN = re.compile(r"^\[([^\]]+)\]\s*(.+)$")

    # Media indicators - patterns to detect media messages
    MEDIA_PATTERNS = {
        "image": [
            r"<attached:\s*[^>]*PHOTO[^>]*>",
            r"<attached:\s*[^>]*\.jpg>",
            r"<attached:\s*[^>]*\.jpeg>",
            r"<attached:\s*[^>]*\.png>",
            r"<attached:\s*[^>]*\.webp>",
            r"image omitted",
            r"<Medien ausgeschlossen>",
            r"IMG-\d+-WA\d+",
        ],
        "video": [
            r"<attached:\s*[^>]*VIDEO[^>]*>",
            r"<attached:\s*[^>]*\.mp4>",
            r"<attached:\s*[^>]*\.mov>",
            r"<attached:\s*[^>]*\.3gp>",
            r"video omitted",
            r"VID-\d+-WA\d+",
        ],
        "audio": [
            r"<attached:\s*[^>]*AUDIO[^>]*>",
            r"<attached:\s*[^>]*\.opus>",
            r"<attached:\s*[^>]*\.mp3>",
            r"<attached:\s*[^>]*\.m4a>",
            r"<attached:\s*[^>]*\.ogg>",
            r"audio omitted",
            r"AUD-\d+-WA\d+",
            r"PTT-\d+",
        ],
        "sticker": [r"sticker omitted", r"<Medien ausgeschlossen>", r"<attached:\s*[^>]*\.webp>"],
        "document": [
            r"<attached:\s*[^>]*\.pdf>",
            r"<attached:\s*[^>]*\.doc>",
            r"<attached:\s*[^>]*\.xlsx>",
            r"document omitted",
        ],
        "gif": [r"GIF omitted", r"<attached:\s*[^>]*\.gif>"],
        "contact": [r"contact card omitted", r"\.vcf"],
        "location": [r"location:"],
    }

    # System message indicators
    SYSTEM_INDICATORS = [
        "Messages and calls are end-to-end encrypted",
        "created group",
        "added",
        "removed",
        "left",
        "changed the subject",
        "changed this group's icon",
        "changed the group description",
        "You're now an admin",
        "security code changed",
        "Missed voice call",
        "Missed video call",
    ]

    def __init__(self):
        self._detected_format = None

    def detect_date_format(self, line: str) -> Optional[tuple]:
        """Detect the date format used in the file."""
        for pattern, fmt in self.DATE_PATTERNS:
            if re.search(pattern, line):
                return (pattern, fmt)
        return None

    def parse_timestamp(self, timestamp_str: str) -> Optional[datetime]:
        """Parse timestamp string to datetime."""
        timestamp_str = clean_unicode(timestamp_str).strip("[]").strip()

        # Formats with zero-padded days (%d) and non-padded days (%-d on Unix, %#d on Windows)
        # We'll try both by using a regex to normalize first
        formats = [
            "%d.%m.%Y, %H:%M:%S",
            "%d.%m.%Y, %H:%M",
            "%d/%m/%Y, %H:%M:%S",
            "%d/%m/%Y, %H:%M",
            "%m/%d/%y, %I:%M:%S %p",
            "%m/%d/%y, %I:%M %p",
            "%d.%m.%y, %H:%M:%S",
            "%d.%m.%y, %H:%M",
        ]

        for fmt in formats:
            try:
                return datetime.strptime(timestamp_str, fmt)
            except ValueError:
                continue

        # Try with manual parsing for single-digit days like "5.10.2024, 13:03:10"
        try:
            # Match pattern: D.MM.YYYY, HH:MM:SS or D.MM.YYYY, HH:MM
            match = re.match(r"(\d{1,2})\.(\d{1,2})\.(\d{4}),\s*(\d{1,2}):(\d{2})(?::(\d{2}))?", timestamp_str)
            if match:
                day, month, year, hour, minute, second = match.groups()
                second = second or "0"
                return datetime(int(year), int(month), int(day), int(hour), int(minute), int(second))
        except (ValueError, AttributeError):
            pass

        logger.warning(f"Could not parse timestamp: {timestamp_str}")
        return None

    def detect_media_type(self, content: str) -> tuple[str, bool, Optional[str]]:
        """Detect if message contains media and its type."""
        # Clean invisible unicode characters for matching
        clean_content = clean_unicode(content)

        for media_type, patterns in self.MEDIA_PATTERNS.items():
            for pattern in patterns:
                if re.search(pattern, clean_content, re.IGNORECASE):
                    # Try to extract filename - clean it too
                    filename_match = re.search(r"<attached:\s*([^>]+)>", clean_content)
                    filename = filename_match.group(1).strip() if filename_match else None
                    return media_type, True, filename

        return "text", False, None

    def is_system_message(self, content: str, sender: str) -> bool:
        """Check if message is a system message."""
        for indicator in self.SYSTEM_INDICATORS:
            if indicator.lower() in content.lower():
                return True
        return False

    def parse_line(self, line: str) -> Optional[ParsedMessage]:
        """Parse a single line from the chat export."""
        # Clean invisible unicode characters from the line
        line = clean_unicode(line).strip()
        if not line:
            return None

        # Try to match message pattern
        match = self.MESSAGE_PATTERN.match(line)
        if match:
            timestamp_str, sender, content = match.groups()
            timestamp = self.parse_timestamp(timestamp_str)

            if not timestamp:
                return None

            sender = sender.strip()
            content = content.strip()

            # Detect media
            message_type, has_media, media_filename = self.detect_media_type(content)

            # Check for system message
            is_system = self.is_system_message(content, sender)
            if is_system:
                message_type = "system"

            return ParsedMessage(
                timestamp=timestamp,
                sender=sender,
                content=content,
                message_type=message_type,
                has_media=has_media,
                media_filename=media_filename,
                is_system=is_system,
            )

        # Try system message pattern (messages without sender)
        sys_match = self.SYSTEM_PATTERN.match(line)
        if sys_match:
            timestamp_str, content = sys_match.groups()
            timestamp = self.parse_timestamp(timestamp_str)

            if timestamp:
                return ParsedMessage(
                    timestamp=timestamp,
                    sender="System",
                    content=content.strip(),
                    message_type="system",
                    is_system=True,
                )

        return None

    def parse_file(self, file_path: str) -> Iterator[ParsedMessage]:
        """Parse a WhatsApp chat export file."""
        current_message: Optional[ParsedMessage] = None

        with open(file_path, "r", encoding="utf-8") as f:
            for line in f:
                parsed = self.parse_line(line)

                if parsed:
                    # Yield previous message if exists
                    if current_message:
                        yield current_message
                    current_message = parsed
                elif current_message and line.strip():
                    # Continuation of previous message (multi-line)
                    clean_line = clean_unicode(line).strip()
                    if clean_line:
                        current_message.content += "\n" + clean_line

            # Yield last message
            if current_message:
                yield current_message

    def parse_content(self, content: str) -> Iterator[ParsedMessage]:
        """Parse WhatsApp chat export from string content."""
        current_message: Optional[ParsedMessage] = None

        for line in content.split("\n"):
            parsed = self.parse_line(line)

            if parsed:
                if current_message:
                    yield current_message
                current_message = parsed
            elif current_message and line.strip():
                # Clean unicode from continuation lines too
                clean_line = clean_unicode(line).strip()
                if clean_line:
                    current_message.content += "\n" + clean_line

        if current_message:
            yield current_message

    async def parse_stream(self, stream) -> Iterator[ParsedMessage]:
        """Parse WhatsApp chat export from async stream."""
        current_message: Optional[ParsedMessage] = None
        buffer = ""

        async for chunk in stream:
            buffer += chunk.decode("utf-8", errors="replace")
            lines = buffer.split("\n")
            buffer = lines[-1]  # Keep incomplete line

            for line in lines[:-1]:
                parsed = self.parse_line(line)

                if parsed:
                    if current_message:
                        yield current_message
                    current_message = parsed
                elif current_message and line.strip():
                    current_message.content += "\n" + line.strip()

        # Process remaining buffer
        if buffer:
            parsed = self.parse_line(buffer)
            if parsed:
                if current_message:
                    yield current_message
                current_message = parsed

        if current_message:
            yield current_message
