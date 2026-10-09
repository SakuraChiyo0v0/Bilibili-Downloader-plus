from dataclasses import asdict, dataclass, field, fields
from functools import lru_cache


@lru_cache(maxsize=None)
def _field_names(cls) -> frozenset[str]:
    return frozenset(f.name for f in fields(cls))


@dataclass
class SyncSourceInfo:
    sync_id: str = ""
    title: str = ""
    url: str = ""
    source_type: str = ""
    enabled: bool = True
    created_time: int = 0
    updated_time: int = 0
    last_checked_time: int = 0
    last_success_time: int = 0
    last_error: str = ""
    last_added_count: int = 0
    known_item_ids: list[str] = field(default_factory=list)
    options: dict = field(default_factory=dict)

    def to_dict(self):
        return asdict(self)

    def from_dict(self, data: dict):
        field_names = _field_names(type(self))

        for key, value in data.items():
            if key in field_names:
                setattr(self, key, value)
