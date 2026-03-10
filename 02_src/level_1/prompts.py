"""
Prompt definitions for Level 1 jurisdiction research queries.

All prompts are self-contained: they include all necessary context
without relying on any external dialog or state.
"""
from typing import Optional


# ---------------------------------------------------------------------------
# 1A: Regulatory Architecture
# ---------------------------------------------------------------------------

PROMPT_1A_TEMPLATE = """\
Research the securities listing and admission to trading framework
in {jurisdiction}.

For each question: provide official local term (original language +
English translation), relevant legal source (law/article),
substantive answer.

1. Are "official listing" and "admission to trading" separate legal
   concepts, or unified? Who decides on each?

2. Who acts as the listing authority — exchange, regulator,
   separate body? Legal basis?

3. Name and type of securities regulator (central bank / commission /
   other)? Governing law?

4. Types of trading venues (regulated market, MTF, OTF, local
   equivalents)? How classified in law?

5. Exchange segmentation: hierarchical listing tiers and/or
   thematic segments? Names of specific tiers and segments.

6. Issuer eligibility separate from per-issue admission?
   Or single procedure?

7. Special regime for secondary listing / cross-listing?

Cite specific legal acts and provisions.

All information must be self-contained. Do not rely on prior context.
{eu_note}"""


def build_prompt_1a(jurisdiction: str, eu_note: Optional[str] = None) -> str:
    """Build the 1A prompt for a given jurisdiction."""
    note_str = ""
    if eu_note:
        note_str = f"\n{eu_note}"
    return PROMPT_1A_TEMPLATE.format(
        jurisdiction=jurisdiction,
        eu_note=note_str,
    )


# ---------------------------------------------------------------------------
# 1B: Institutional Factors
# ---------------------------------------------------------------------------

# Output schema for 1B (JSON)
SCHEMA_1B = {
    "type": "object",
    "properties": {
        "jurisdiction": {"type": "string"},
        "qualitative_factors": {
            "type": "object",
            "properties": {
                "F3_private_enforcement": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "assessment": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
                "F8_ownership_concentration": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "state_share_pct": {"type": "string"},
                        "assessment": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
                "F9_investor_base": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "institutional_share_pct": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
                "F12_exchange_as_sro": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "assessment": {"type": "string"},
                        "source": {"type": "string"},
                    },
                },
            },
        },
        "preloaded_verification": {
            "type": "object",
            "properties": {
                "F1_legal_family": {
                    "type": "object",
                    "properties": {
                        "confirmed": {"type": "boolean"},
                        "corrected_value": {"type": ["string", "null"]},
                        "source": {"type": "string"},
                    },
                },
                "F11_regulator_type": {
                    "type": "object",
                    "properties": {
                        "confirmed": {"type": "boolean"},
                        "corrected_value": {"type": ["string", "null"]},
                        "source": {"type": "string"},
                    },
                },
                "F7_market_depth": {
                    "type": "object",
                    "properties": {
                        "confirmed": {"type": "boolean"},
                        "corrected_value": {"type": ["string", "null"]},
                        "source": {"type": "string"},
                    },
                },
            },
        },
    },
}

PROMPT_1B_TEMPLATE = """\
Research the following institutional characteristics of {jurisdiction}
securities markets. For each factor provide: value assessment,
substantive explanation, and source.

1. Private enforcement (F3): What mechanisms exist for private
   investor lawsuits against issuers/intermediaries for securities
   violations? Are there class actions, derivative suits?
   Level: high / medium / low / absent.

2. Ownership concentration (F8): Is share ownership dispersed
   (many small shareholders) or concentrated (controlling blocks
   common)? Approximate state sector share if available.
   Level: dispersed / moderate / concentrated.

3. Investor base structure (F9): Predominantly institutional
   investors, retail investors, or mixed?
   Approximate institutional share % if available.

4. Exchange as SRO (F12): Does the exchange have self-regulatory
   authority — listing enforcement, disciplinary powers over
   members? Or is it purely a market operator?
   Level: full SRO / partial / operator only.

Also verify (confirm or correct) these pre-loaded values:
- Legal family (F1): [common law / civil law / mixed / other]
- Regulator type (F11): [central bank / commission / supranational / other], regulator name
- Market depth (F7): market capitalisation as % of GDP (approximate)

All prompts are self-contained. Do not rely on prior context.
Jurisdiction: {jurisdiction}"""


def build_prompt_1b(jurisdiction: str) -> str:
    """Build the 1B prompt for a given jurisdiction."""
    return PROMPT_1B_TEMPLATE.format(jurisdiction=jurisdiction)


# ---------------------------------------------------------------------------
# 1C: Venue Landscape
# ---------------------------------------------------------------------------

# Output schema for 1C (JSON)
SCHEMA_1C = {
    "type": "object",
    "properties": {
        "jurisdiction": {"type": "string"},
        "operators": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "operator_name": {"type": "string"},
                    "venues": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "venue_name_local": {"type": "string"},
                                "venue_name_english": {"type": "string"},
                                "market_type": {"type": "string"},
                                "own_rulebook": {"type": "string"},
                                "tiers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                    },
                                },
                                "segments": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                    },
                                },
                                "regime_modifiers": {
                                    "type": "array",
                                    "items": {
                                        "type": "object",
                                        "properties": {
                                            "name": {"type": "string"},
                                            "description": {"type": "string"},
                                        },
                                    },
                                },
                                "instrument_classes": {
                                    "type": "object",
                                    "properties": {
                                        "equities": {
                                            "type": "object",
                                            "properties": {
                                                "admitted": {"type": "boolean"},
                                            },
                                        },
                                        "bonds": {
                                            "type": "object",
                                            "properties": {
                                                "admitted": {"type": "boolean"},
                                            },
                                        },
                                        "funds": {
                                            "type": "object",
                                            "properties": {
                                                "admitted": {"type": "boolean"},
                                            },
                                        },
                                        "depositary_receipts": {
                                            "type": "object",
                                            "properties": {
                                                "admitted": {"type": "boolean"},
                                            },
                                        },
                                    },
                                },
                                "scale": {
                                    "type": "object",
                                    "properties": {
                                        "listed_issuers": {"type": "string"},
                                        "market_cap": {"type": "string"},
                                    },
                                },
                                "source": {"type": "string"},
                            },
                        },
                    },
                },
            },
        },
    },
}

PROMPT_1C_TEMPLATE = """\
Provide an overview of all securities trading venues in {jurisdiction}.

Context from regulatory research:
- Regulator: {regulator_context}
- Market types: {market_types_context}

DEFINITIONS — use these when classifying entities:

DEFINITION — Market Operator:
An institution (company or group) that owns and operates one or more trading venues.
A single operator may run multiple venues with fundamentally different regulatory
frameworks. The operator is NOT the unit of analysis — the venue is.
Example: London Stock Exchange Group (operator) runs Main Market and AIM (two
separate venues). Do not treat the operator as a venue.

DEFINITION — Trading Venue (= "venue"):
A market with its own regulatory framework and its own set of admission rules,
operated by a market operator. This is the primary structural unit of analysis.

CLASSIFICATION TEST — When to treat two parts of the same exchange as separate venues:
If they have DIFFERENT regulatory status (e.g., one is a Regulated Market and the
other is an MTF), OR they have SEPARATE rulebooks governing admission, OR the type
of required intermediary differs (e.g., Sponsor vs. Nominated Adviser) — treat them
as separate venues.
If they share the SAME rulebook and the SAME regulatory status, but differ in the
STRICTNESS of quantitative thresholds — they are tiers within one venue, not
separate venues.

Examples:
- LSE Main Market (Regulated Market) and AIM (MTF) → TWO separate venues
- Nasdaq Global Select Market and Nasdaq Capital Market → ONE venue, two tiers
  (same regulatory framework, different threshold levels)
- HKEX Main Board and GEM → TWO separate venues (different admission rules
  and thresholds, different target issuers)

DEFINITION — Market Type:
The regulatory classification of a venue. Key distinction: venues where admission
rules are set by legislation/regulator ("Regulated Market") vs. venues where rules
are set primarily by the operator itself (MTF, OTF, or equivalent).
If the jurisdiction does not have a formal market type classification, record the
factual distribution of rule-setting authority.

DEFINITION — Listing Tier:
A hierarchical level within a single venue that determines the strictness of
admission and continuing obligation requirements. Higher tiers impose stricter
requirements and signal higher quality to investors.

CLASSIFICATION TEST — Is it a tier or a separate venue?
A tier shares the SAME regulatory framework and rulebook as other tiers of the same
venue, but sets HIGHER or LOWER quantitative thresholds.
If the entity has its OWN rulebook or a DIFFERENT regulatory status — it is a
separate venue, not a tier.

CLASSIFICATION TEST — Is it a tier or a segment?
A tier creates a vertical hierarchy: stricter vs. less strict.
A segment creates a horizontal grouping: thematic or sectoral.

NOTE: Not all venues have tiers. Record this as "flat structure — no listing tiers"
rather than leaving the field empty.

DEFINITION — Specialized Segment:
A thematic or sectoral subdivision within a venue, with ADDITIONAL criteria on top
of the venue's base requirements. A segment does NOT replace the base requirements —
it adds to them.

CLASSIFICATION TEST — Is it a segment or a tier?
If the entity imposes thematically specific requirements (industry sector, ESG, size
category) rather than generally stricter ones — it is a segment.

DEFINITION — Admission Regime Modifier:
A set of rule modifications that alter the standard admission regime for a specific
TYPE of issuer or instrument, without creating a separate venue, tier, or segment.

CLASSIFICATION TEST — Is it a modifier, a segment, or a tier?
If the entity changes WHO is eligible (biotech companies, SPACs, WVR companies)
rather than WHERE the issuer is listed — it is a modifier.

KEY DISTINCTION FROM SEGMENT: A segment is a PLACE on the exchange (issuers are
"in" the segment). A modifier is a RULE ADJUSTMENT applied to a category of issuer.

Examples of modifiers:
- HKEX Chapter 18A (Biotech) → modifier
- HKEX Chapter 18B (SPAC) → modifier
- HKEX Chapter 8A (WVR) → modifier

Do NOT list modifiers as separate venues, tiers, or segments in your output.
List them in the regime_modifiers array of the venue they belong to.

For each market operator and its venues, provide:
1. Operator name
2. For each venue operated:
   a. Official name (local language and English)
   b. Market type (regulated market / MTF / OTF / other; or factual
      description of rule-setting authority if no formal classification)
   c. Own rulebook (yes / no; name of rulebook if yes)
   d. Listing tiers — names and brief description of each tier; if none,
      record "flat structure — no listing tiers"
   e. Specialised segments (SME, ESG, technology, REIT, etc.) — names
      and brief description; do NOT list modifiers here
   f. Admission regime modifiers — special chapters or issuer-type rules
      (e.g., biotech, SPAC, WVR) that adjust admission rules without
      creating a separate venue, tier, or segment
   g. Instrument classes admitted: equities, bonds, funds,
      depositary receipts (admitted: yes/no for each)
   h. Approximate scale (number of listed issuers, market cap)

All information must be self-contained. Do not rely on prior context.
Jurisdiction: {jurisdiction}"""


def build_prompt_1c(
    jurisdiction: str,
    regulator_context: str = "to be determined",
    market_types_context: str = "to be determined",
) -> str:
    """Build the 1C prompt for a given jurisdiction."""
    return PROMPT_1C_TEMPLATE.format(
        jurisdiction=jurisdiction,
        regulator_context=regulator_context,
        market_types_context=market_types_context,
    )
