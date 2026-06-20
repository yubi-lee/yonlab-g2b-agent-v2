from typing import Any

from pydantic import BaseModel, Field


class BidNotice(BaseModel):
    notice_id: str = ""
    title: str = ""
    agency: str = ""
    budget_amount: int | None = None
    deadline: str | None = None
    region: str = ""
    contract_type: str = ""
    business_type: str = ""
    qualification_text: str = ""
    description: str = ""
    keywords: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)
    preferences: list[str] = Field(default_factory=list)
    categories: list[str] = Field(default_factory=list)
    raw_source: dict[str, Any] = Field(default_factory=dict)

    def searchable_text(self) -> str:
        values: list[Any] = [
            self.notice_id,
            self.title,
            self.agency,
            self.region,
            self.contract_type,
            self.business_type,
            self.qualification_text,
            self.description,
            *self.keywords,
            *self.requirements,
            *self.restrictions,
            *self.preferences,
            *self.categories,
            *self.raw_source.values(),
        ]
        return " ".join(_stringify(value) for value in values if value not in (None, "")).casefold()


def _stringify(value: Any) -> str:
    if isinstance(value, list | tuple | set):
        return " ".join(_stringify(item) for item in value)
    if isinstance(value, dict):
        return " ".join(f"{key} {_stringify(item)}" for key, item in value.items())
    return str(value)
