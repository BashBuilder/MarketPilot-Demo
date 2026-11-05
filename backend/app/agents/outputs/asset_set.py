"""Generated visual assets recorded by the Designer agent."""

from typing import Annotated, Self

from pydantic import Field, field_validator, model_validator

from app.agents.outputs.base import OutputModel


class Asset(OutputModel):
    """Metadata for one generated file; binaries live outside the database."""

    uri: Annotated[str, Field(min_length=5)]
    checksum: Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]
    model: Annotated[str, Field(min_length=2)]
    seed: Annotated[int, Field(ge=0)]
    prompt: Annotated[str, Field(min_length=5)]

    @field_validator("uri")
    @classmethod
    def _uri_has_no_whitespace(cls, value: str) -> str:
        if any(char.isspace() for char in value):
            raise ValueError("uri must not contain whitespace")
        return value


class AssetSet(OutputModel):
    """All assets generated for a campaign version."""

    assets: Annotated[list[Asset], Field(min_length=1)]

    @model_validator(mode="after")
    def _asset_uris_unique(self) -> Self:
        uris = [asset.uri.casefold() for asset in self.assets]
        if len(uris) != len(set(uris)):
            raise ValueError("asset uris must be unique")
        return self
