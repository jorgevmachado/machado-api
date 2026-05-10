from typing import Any

from pydantic import BaseModel, ConfigDict, Field, create_model


class Message(BaseModel):
    message: str


class FilterPage[TFilterPage](BaseModel):
    model_config = ConfigDict()

    page: int | None = Field(None, ge=0)
    offset: int | None = Field(None, ge=0)
    limit: int | None = Field(None, ge=1)
    order_by: str | None = Field(None)
    clean_cache: bool | None = Field(None)

    @classmethod
    def _build_dynamic(cls: type[TFilterPage], payload: dict[str, Any]) -> TFilterPage:
        extra_fields = {key for key in payload if key not in cls.model_fields}

        if extra_fields:
            dynamic_cls = create_model(
                f"{cls.__name__}Dynamic",
                __base__=cls,
                **{key: (Any | None, None) for key in extra_fields},
            )
            return dynamic_cls.model_validate(payload)

        return cls.model_validate(payload)

    def with_updates(self, **updates: Any) -> TFilterPage:
        payload = self.model_dump(exclude_none=True)
        payload.update(
            {key: value for key, value in updates.items() if value is not None}
        )
        return self._build_dynamic(payload)

    @classmethod
    def build(
        cls: type[TFilterPage], page_filter: TFilterPage | None = None, **updates: Any
    ) -> TFilterPage:
        payload = (
            page_filter.model_dump(exclude_none=True) if page_filter is not None else {}
        )
        payload.update(
            {key: value for key, value in updates.items() if value is not None}
        )
        return cls._build_dynamic(payload)
