from dataclasses import dataclass, field


@dataclass(frozen=True)
class BidNotice:
    title: str
    description: str = ""
    notice_id: str = ""
    requirements: tuple[str, ...] = field(default_factory=tuple)
    restrictions: tuple[str, ...] = field(default_factory=tuple)
    preferences: tuple[str, ...] = field(default_factory=tuple)
    categories: tuple[str, ...] = field(default_factory=tuple)

    def searchable_text(self) -> str:
        parts = (
            self.notice_id,
            self.title,
            self.description,
            *self.requirements,
            *self.restrictions,
            *self.preferences,
            *self.categories,
        )
        return " ".join(part for part in parts if part).casefold()
