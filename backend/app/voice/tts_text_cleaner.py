"""TTS Text Cleaner — strip formatting artefacts for speech synthesis.

Pure-function module used by TTSTextCleaner FrameProcessor in the
voice pipeline. Keeps Orpheus emotion tags when requested.
"""

import re

# ── Orpheus-specific patterns to PRESERVE ────────────────────────
_ORPHEUS_EMOTION_TAGS = {
    "laugh", "chuckle", "sigh", "gasp", "cough", "sniffle", "groan", "yawn",
}
_ORPHEUS_VOCAL_DIRS = {
    # Original set
    "cheerful", "whisper", "excited", "sad", "angry", "calm", "surprised",
    # Extended from Groq Orpheus docs
    "dramatically", "professionally", "authoritatively",
    "singsong", "breathy", "gravelly whisper", "rapid babbling",
}

# Build regex that matches Orpheus tags: <laugh>, <chuckle>, etc.
_ORPHEUS_TAG_PATTERN = re.compile(
    r"<(?:" + "|".join(_ORPHEUS_EMOTION_TAGS) + r")>",
    re.IGNORECASE,
)
# Vocal directions: [cheerful], [whisper], [dramatically], etc.
# Sort by length descending so multi-word directions match before sub-patterns
_ORPHEUS_DIR_PATTERN = re.compile(
    r"\[(?:" + "|".join(sorted(_ORPHEUS_VOCAL_DIRS, key=len, reverse=True)) + r")\]",
    re.IGNORECASE,
)

# ── Patterns to STRIP ───────────────────────────────────────────

# Markdown bold/italic with asterisks: **text**, *text*
_MD_ASTERISK = re.compile(r"\*{1,3}")
# Markdown bold/italic with underscores (wrapping only, not mid-word):
# _text_ or __text__ but NOT navigate_to
_MD_UNDERSCORE_WRAP = re.compile(r"(?<!\w)_{1,3}(?=\S)|(?<=\S)_{1,3}(?!\w)")
# Markdown headers: # Header, ## Header, ### Header
_MD_HEADERS = re.compile(r"^#{1,6}\s+", re.MULTILINE)
# Markdown bullet lists: - item, * item (only at line start)
_MD_BULLETS = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
# Numbered lists: 1. item, 2. item
_MD_NUMBERED = re.compile(r"^\s*\d+\.\s+", re.MULTILINE)
# Backtick code: `code` → keep inner text. Handles single backticks only.
_MD_BACKTICK_WRAP = re.compile(r"`([^`]*)`")
# Triple backtick blocks ```...```
_MD_TRIPLE_BACKTICK = re.compile(r"```[^`]*```", re.DOTALL)
# Markdown links: [text](url) → keep text
_MD_LINKS = re.compile(r"\[([^\]]+)\]\([^)]+\)")
# URLs: http://... or https://...
_URLS = re.compile(r"https?://\S+")
# Parenthetical asides: (e.g., ...), (i.e., ...)
_PARENS_ASIDE = re.compile(r"\((?:e\.g\.|i\.e\.|etc\.)[^)]*\)", re.IGNORECASE)
# Ellipsis: ... or …
_ELLIPSIS = re.compile(r"\.{3,}|…")
# Em-dash: — or --
_EM_DASH = re.compile(r"—|–|--")
# Multiple spaces
_MULTI_SPACE = re.compile(r" {2,}")
# Multiple periods (after other cleanup)
_MULTI_PERIOD = re.compile(r"\.(\s*\.)+")
# Emoji: broad Unicode range for common emoji
_EMOJI = re.compile(
    "["
    "\U0001F600-\U0001F64F"  # Emoticons
    "\U0001F300-\U0001F5FF"  # Misc Symbols and Pictographs
    "\U0001F680-\U0001F6FF"  # Transport and Map
    "\U0001F1E0-\U0001F1FF"  # Flags
    "\U00002702-\U000027B0"  # Dingbats
    "\U0001F900-\U0001F9FF"  # Supplemental Symbols
    "\U0001FA00-\U0001FA6F"  # Chess Symbols
    "\U0001FA70-\U0001FAFF"  # Symbols Extended-A
    "\U00002600-\U000026FF"  # Misc symbols
    "\U0000FE00-\U0000FE0F"  # Variation Selectors
    "\U0000200D"             # ZWJ
    "\U00002B50"             # Star
    "\U0000203C-\U00002049"  # Exclamation marks
    "]+",
    flags=re.UNICODE,
)

# Pattern to strip Orpheus tags when NOT using Orpheus
_STRIP_ORPHEUS_TAGS = re.compile(
    r"<(?:" + "|".join(_ORPHEUS_EMOTION_TAGS) + r")>",
    re.IGNORECASE,
)
_STRIP_ORPHEUS_DIRS = re.compile(
    r"\[(?:" + "|".join(_ORPHEUS_VOCAL_DIRS) + r")\]",
    re.IGNORECASE,
)


def clean_text_for_tts(text: str, preserve_orpheus_tags: bool = True) -> str:
    """Clean LLM output text for TTS consumption.

    Strips markdown formatting, URLs, emoji, and excess punctuation
    while optionally preserving Orpheus emotion tags.

    Args:
        text: Raw LLM output text.
        preserve_orpheus_tags: If True, keep <laugh>, [cheerful] etc.
            Set to False for non-Orpheus TTS providers.

    Returns:
        Cleaned text ready for TTS engine.
    """
    if not text:
        return text

    # Phase 1: Protect Orpheus tags by replacing with placeholders
    placeholders: list[tuple[str, str]] = []
    if preserve_orpheus_tags:
        counter = [0]

        def _replace_tag(match: re.Match) -> str:
            ph = f"XORPHTAG{counter[0]}X"
            placeholders.append((ph, match.group()))
            counter[0] += 1
            return ph

        def _replace_dir(match: re.Match) -> str:
            ph = f"XORPHDIR{counter[0]}X"
            placeholders.append((ph, match.group()))
            counter[0] += 1
            return ph

        text = _ORPHEUS_TAG_PATTERN.sub(_replace_tag, text)
        text = _ORPHEUS_DIR_PATTERN.sub(_replace_dir, text)
    else:
        # Strip Orpheus tags entirely when not using Orpheus
        text = _STRIP_ORPHEUS_TAGS.sub("", text)
        text = _STRIP_ORPHEUS_DIRS.sub("", text)

    # Phase 2: Strip formatting
    # Order matters: links before URLs, backticks before bold/italic
    text = _MD_TRIPLE_BACKTICK.sub("", text)     # Remove ```code``` blocks
    text = _MD_BACKTICK_WRAP.sub(r"\1", text)    # `code` → code (keep inner)
    text = _MD_LINKS.sub(r"\1", text)             # [text](url) → text
    text = _URLS.sub("", text)                    # Remove bare URLs
    text = _PARENS_ASIDE.sub("", text)            # Remove (e.g., ...)
    text = _MD_HEADERS.sub("", text)              # Remove # headers
    text = _MD_BULLETS.sub("", text)              # Remove - bullets
    text = _MD_NUMBERED.sub("", text)             # Remove 1. numbering
    text = _MD_ASTERISK.sub("", text)             # Remove * formatting
    text = _MD_UNDERSCORE_WRAP.sub("", text)      # Remove _wrap_ formatting
    text = _EMOJI.sub("", text)                   # Remove emoji

    # Phase 3: Normalize punctuation
    text = _ELLIPSIS.sub(",", text)               # ... → comma (natural pause)
    text = _EM_DASH.sub(",", text)                # — → comma
    text = _MULTI_PERIOD.sub(".", text)           # .. → .

    # Phase 4: Restore Orpheus placeholders
    for ph, orig in placeholders:
        text = text.replace(ph, orig)

    # Phase 5: Final cleanup
    text = _MULTI_SPACE.sub(" ", text)
    text = text.strip()

    return text
