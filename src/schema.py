from typing import Literal, Optional
from pydantic import BaseModel, Field


class PICO(BaseModel):
    """Structured extraction target for an RCT abstract."""

    population: str = Field(
        description="Study population: age range and condition, one phrase"
    )
    intervention: str = Field(
        description="Treatment arm, including drug name and dose if stated"
    )
    comparator: str = Field(
        description="Control arm: 'placebo', 'usual care', a named drug, or 'none'"
    )
    primary_outcome: str = Field(
        description="The stated primary endpoint only, not secondary endpoints"
    )
    effect_direction: Literal[
        "intervention_favored",
        "comparator_favored",
        "no_difference",
        "unclear",
    ] = Field(description="Direction of effect on the PRIMARY outcome only")
    sample_size: Optional[int] = Field(
        default=None, description="Total participants randomized across all arms"
    )


SYSTEM_PROMPT = """You extract structured PICO data from randomized controlled trial abstracts.

Return ONLY a JSON object with exactly these keys:
population, intervention, comparator, primary_outcome, effect_direction, sample_size

effect_direction must be exactly one of:
intervention_favored, comparator_favored, no_difference, unclear

sample_size is an integer, or null if not stated.

No prose. No explanation. No markdown code fences. JSON only."""
