import re


TAG_PATTERN = re.compile(r"#([A-Za-z0-9_]{1,64})")


def extract_tags(text: str) -> list[str]:
    return sorted({match.group(1).lower() for match in TAG_PATTERN.finditer(text)})

