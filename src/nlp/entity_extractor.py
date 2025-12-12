import re
from typing import Optional


class EntityExtractor:
    patterns = {
        "nomor_pelanggan": re.compile(r"(?:id|no)\s*(?:pelanggan|langganan)\s*(\d{4,})"),
        "nama_wifi": re.compile(r"ssid\s+([a-z0-9_\-]+)", re.IGNORECASE),
        "kendala_internet": re.compile(r"(los|lampu merah|putus|mati total)"),
    }

    def extract(self, text: str) -> Optional[str]:
        lowered = text.lower()
        for entity, pattern in self.patterns.items():
            match = pattern.search(lowered)
            if match:
                return f"{entity}:{match.group(1)}" if match.groups() else entity
        return None
