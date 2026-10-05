from __future__ import annotations

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


# Weight maps use the same percentage scale and keys as the frontend controls.
Percentage = Annotated[float, Field(ge=0, le=100, allow_inf_nan=False)]
TagWeight = Annotated[float, Field(le=100, allow_inf_nan=False)]
Context = Literal["mechanics", "narrative", "vibe", "structure_loop", "identity", "setting", "music"]
Match = Literal["vector", "genre", "appeal", "music"]
Appeal = Literal["challenge", "complexity", "pace", "narrative_focus", "social_energy", "creativity"]
GenreBranch = Literal["primary", "sub", "sub_sub", "traits"]


class RecommendationWeights(BaseModel):
    model_config = ConfigDict(extra="ignore")

    match: dict[Match, Percentage] | None = None
    context: dict[Context, Percentage] | None = None
    appeal: dict[Appeal, Percentage] | None = None
    tags: dict[Context, dict[str, TagWeight]] | None = None
    genres: dict[GenreBranch, list[str] | str] | None = None

    @field_validator("tags")
    @classmethod
    def clamp_tag_weights(cls, tags: dict[str, dict[str, float]] | None) -> dict[str, dict[str, float]] | None:
        if tags is None:
            return None
        return {
            context: {
                tag: max(0.0, weight)
                for tag, weight in entries.items()
            }
            for context, entries in tags.items()
        }


class RecommendationRequest(BaseModel):
    model_config = ConfigDict(extra="ignore")

    appid: int
    limit: int = Field(default=20, ge=1, le=50)
    weights: RecommendationWeights = Field(default_factory=RecommendationWeights)
