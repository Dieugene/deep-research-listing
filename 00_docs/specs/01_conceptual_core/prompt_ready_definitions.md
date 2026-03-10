# Prompt-Ready Definitions
## For literal insertion into pipeline prompts

**Version:** 0.1
**Date:** 2026-03-09
**Usage:** Copy the relevant definition block into the prompt text verbatim. Do not paraphrase or summarize — the wording is calibrated to prevent classification errors by the AI agent.

---

## Level 1B (Landscape) and Level 2A (Venue Structure)

---

### DEF-B02: Market Operator

```
DEFINITION — Market Operator:
An institution (company or group) that owns and operates one or more trading venues.
A single operator may run multiple venues with fundamentally different regulatory
frameworks. The operator is NOT the unit of analysis — the venue is.
Example: London Stock Exchange Group (operator) runs Main Market and AIM (two
separate venues). Do not treat the operator as a venue.
```

---

### DEF-A02: Trading Venue

```
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
- SSE Main Board and STAR Market → TWO separate venues (STAR has its own
  rulebook and distinct admission criteria)
```

---

### DEF-A03: Market Type

```
DEFINITION — Market Type:
The regulatory classification of a venue, which determines the source and scope of
applicable admission rules. The key distinction is between venues where admission
rules are set by legislation/regulator ("Regulated Market" in EU terminology) and
venues where rules are set primarily by the operator itself (MTF, OTF, or equivalent).

RELATIONSHIP TO VENUE: Market type is a property of a venue. Two venues operated by
the same operator often have different market types — this is one of the primary
reasons they are separate venues.

If the jurisdiction does not have a formal market type classification (e.g., non-EU
jurisdictions), record the factual distribution of rule-setting authority: who sets
admission rules — the regulator, the exchange, or both.
```

---

### DEF-A05: Listing Tier

```
DEFINITION — Listing Tier:
A hierarchical level within a single venue that determines the strictness of
admission and continuing obligation requirements. Higher tiers impose stricter
requirements and signal higher quality to investors.

CLASSIFICATION TEST — Is it a tier or a separate venue?
A tier shares the SAME regulatory framework and rulebook as other tiers of the
same venue, but sets HIGHER or LOWER quantitative thresholds. The requirements
of a higher tier are a superset of the lower tier's requirements.
If the entity has its OWN rulebook or a DIFFERENT regulatory status — it is a
separate venue, not a tier.

CLASSIFICATION TEST — Is it a tier or a segment?
A tier creates a vertical hierarchy: stricter vs. less strict. An issuer "qualifies"
for a higher tier by meeting more demanding thresholds.
A segment creates a horizontal grouping: thematic or sectoral. An issuer "belongs"
to a segment based on its industry, business model, or purpose — not because it
meets stricter general requirements.

Examples:
- MOEX: First Level, Second Level, Third Level → tiers (vertical hierarchy of
  strictness)
- Nasdaq: Global Select, Global, Capital → tiers
- LSE Main Market pre-2024: Premium, Standard → tiers
- LSE Main Market post-2024: single tier (no tiering)

NOTE: Not all venues have tiers. For some instrument classes (especially bonds),
tiered listing does not exist on many exchanges. Record this as "flat structure —
no listing tiers" rather than leaving the field empty.
```

---

### DEF-A04: Specialized Segment

```
DEFINITION — Specialized Segment:
A thematic or sectoral subdivision within a venue, with ADDITIONAL criteria on top
of the venue's base requirements (and, if applicable, on top of a tier's requirements).
A segment does NOT replace the base requirements — it adds to them.

CLASSIFICATION TEST — Is it a segment or a tier?
If the entity imposes requirements that are thematically specific (industry sector,
ESG criteria, company size category, innovation focus) rather than generally stricter,
it is a segment. If an issuer must meet ALL base venue/tier requirements PLUS
additional thematic criteria — it is a segment.
If the entity defines a general hierarchy of strictness with no thematic filter —
it is a tier.

CLASSIFICATION TEST — Is it a segment or a separate venue?
If the entity operates under the SAME rulebook and regulatory framework as the rest
of the venue, with additional overlay rules — it is a segment. If it has its OWN
rulebook or different regulatory status — it is a separate venue.

Examples:
- MOEX: "Innovation and Investment Market", "Growth Sector", "Sustainable Development
  Sector" → segments (thematic overlays on top of standard tier requirements)
- SGX: Catalist → separate venue (own rulebook, own sponsor regime), NOT a segment
  of Mainboard
```

---

### DEF-G08: Admission Regime Modifier

```
DEFINITION — Admission Regime Modifier:
A set of rule modifications that alter the standard admission regime for a specific
TYPE of issuer or instrument, without creating a separate venue, tier, or segment.
Modifiers adjust specific parameters (thresholds, procedures, disclosure requirements)
of the base regime while the issuer remains within the same venue and tier.

CLASSIFICATION TEST — Is it a modifier, a segment, or a tier?
If the entity changes WHO is eligible (a specific category of issuer — e.g., biotech
companies without revenue, SPACs, companies with weighted voting rights) rather than
WHERE the issuer is listed — it is a modifier, not a segment or tier. The issuer is
still listed on the same venue and tier; the rules are adjusted for its category.

KEY DISTINCTION FROM SEGMENT: A segment is a PLACE on the exchange (issuers are
"in" the segment). A modifier is a RULE ADJUSTMENT applied to a category of issuer
regardless of which segment they may also belong to.

Examples:
- HKEX Chapter 18A (Biotech) → modifier (adjusts Main Board rules for pre-revenue
  biotech companies; they are still listed on Main Board, not in a separate segment)
- HKEX Chapter 8A (WVR) → modifier (adjusts rules for companies with weighted
  voting rights)
- HKEX Chapter 18B (SPAC) → modifier
- Nasdaq IM-5101-2 (SPAC-specific standards) → modifier
- NYSE Section 102.06 (SPAC) → modifier

NOTE: When you encounter a special chapter or section in a rulebook that applies to
a specific issuer type — classify it as a modifier unless it explicitly creates a
separate named market segment that issuers are "admitted to".
```

---

## Level 3 (Cell)

---

### DEF-G01: Admission Regime

```
DEFINITION — Admission Regime:
The specific combination of rules, procedures, and requirements that apply to a
particular admission case. An admission regime is determined by three coordinates:
venue × listing tier (if any) × instrument class/subclass.

Each unique combination of these three coordinates potentially has its own regime
and constitutes a separate "cell" for research purposes.

WHEN TO CREATE A SEPARATE CELL: If changing any one of the three coordinates changes
the set of applicable admission rules — that is a separate cell. If two instrument
subclasses share identical admission rules on the same venue and tier — they can be
merged into one cell with a note.

Example: HKEX Main Board × [no tier] × Equities = one cell.
         HKEX Main Board × [no tier] × Debt = a different cell (different rules).
         HKEX GEM × [no tier] × Equities = a different cell (different venue).
```

---

### DEF-G06: Secondary Admission

```
DEFINITION — Secondary Admission (cross-listing / secondary listing):
Admission of a financial instrument to a venue where it is NOT primarily listed,
when the instrument is already admitted on another venue (domestic or foreign).
Secondary admission is NOT a separate object in the model — it is a variant of
primary admission with the attribute "already listed elsewhere".

WHEN TO QUERY SEPARATELY: Always ask whether the venue has a SPECIAL REGIME for
secondary admissions (fast-track procedures, reduced requirements, exemptions from
certain criteria). If yes — record which specific requirements are reduced or waived
compared to primary admission. If no special regime exists — record that the standard
primary admission rules apply in full.

Do NOT create a separate research cell for secondary admission. Record it as a
property of the primary admission cell: "secondary admission regime exists: yes/no;
if yes: [list of modifications]".
```

---

### DEF-G04: Listing/Admission Architecture

```
DEFINITION — Listing/Admission Architecture:
In some jurisdictions, "official listing" (inclusion in an official register
maintained by a listing authority) and "admission to trading" (permission to
trade on a venue) are TWO SEPARATE legal acts, performed by different bodies,
under different rules. In other jurisdictions, these are merged into a single
process.

VALUES:
- "merged" — listing and admission to trading are a single procedure,
  single decision-maker. Most jurisdictions.
- "split" — listing and admission are separate. An instrument can be admitted
  to trading without being officially listed. Example: UK (FCA Official List
  vs. LSE admission to trading under ADS).
- "mixed" — varies by market type or venue within the jurisdiction.

This is recorded at Level 1 (jurisdiction). It determines whether the Level 2
prompt should ask about admission-without-listing paths.
```

---

### DEF-V04: Issuer vs. Instrument Requirements

```
DEFINITION — Separation of Issuer and Instrument Requirements:
Within any admission regime, requirements fall into two categories:
- ISSUER requirements: conditions on the issuer as an entity (financial history,
  profitability, corporate governance, board composition, auditor standards).
- INSTRUMENT requirements: conditions on the specific security being admitted
  (free float, minimum shares outstanding, price, distribution among holders).

This is an ANALYTICAL distinction that applies to ALL jurisdictions. However,
jurisdictions differ in an ARCHITECTURAL fact: whether the issuer is admitted
separately from its instruments.

WHAT TO RECORD:
(1) ARCHITECTURAL FACT: Does this venue admit the issuer separately (issuer
    "eligibility" as a one-time process, after which individual issues are admitted
    via simplified procedure)? Or is there a single admission procedure where both
    issuer and instrument requirements are checked together?
(2) SPECIFIC REQUIREMENTS: Regardless of the architecture, list requirements in
    two groups — those applying to the issuer and those applying to the instrument.

Do NOT conflate these two levels. The architectural fact is recorded once per venue.
The specific requirements are recorded per cell (venue × tier × instrument class).
```

---

## Cross-cutting (All Levels)

---

### DEF-SUPRA: Supranational Framework

```
DEFINITION — Supranational Framework:
A set of rules established by a supranational body that are binding on (or formally
transposed into the law of) multiple jurisdictions, creating a common regulatory
layer above national regulation. The supranational framework sets minimum standards
or harmonized rules; national jurisdictions may add requirements but cannot reduce
them below the supranational floor.

CLASSIFICATION TEST — Is it a supranational framework?
(1) Is there a formal legal instrument (directive, regulation, treaty) that REQUIRES
    member jurisdictions to implement specific admission-related rules? → YES =
    supranational framework.
(2) Is it a bilateral or multilateral ARRANGEMENT between exchanges or regulators
    that facilitates cross-border access but does NOT impose binding admission rules?
    → NO = not a supranational framework. Record as a cross-border arrangement.

Examples:
- EU MiFID II / MiFIR → supranational framework (defines market types, sets
  requirements for Regulated Markets and MTFs, binding on all EU/EEA members)
- EU Prospectus Regulation → supranational framework
- EU Transparency Directive → supranational framework
- Stock Connect (Shanghai–Hong Kong) → NOT a supranational framework (bilateral
  market access arrangement; each side retains its own admission rules)
- IOSCO Objectives and Principles → NOT a supranational framework (non-binding
  standards; no legal obligation to implement)
- Mutual recognition agreements between regulators → NOT a supranational framework
  (facilitate access but do not harmonize admission rules)

WHEN A SUPRANATIONAL FRAMEWORK EXISTS: Record the jurisdiction as having TWO layers
of regulation — supranational (e.g., "EU") and national (e.g., "France"). Note which
admission rules come from which layer. Some requirements are set at the supranational
level and cannot be modified nationally; others are set nationally within the
supranational framework's boundaries.
```

---

## Summary Table

| ID | Concept | Level | Core v0 ref |
|----|---------|-------|-------------|
| DEF-B02 | Market Operator | 1B, 2A | Б02 |
| DEF-A02 | Trading Venue | 1B, 2A | А02 |
| DEF-A03 | Market Type | 1B, 2A | А03 |
| DEF-A05 | Listing Tier | 2A | А05 |
| DEF-A04 | Specialized Segment | 2A | А04 |
| DEF-G08 | Admission Regime Modifier | 2A, 3 | **NEW — not in v0** |
| DEF-G01 | Admission Regime | 3 | Г01 |
| DEF-G06 | Secondary Admission | 3 | Г06 |
| DEF-G04 | Listing/Admission Architecture | 1A, 2A | Г04 |
| DEF-V04 | Issuer vs. Instrument Requirements | 3 | В04 |
| DEF-SUPRA | Supranational Framework | Cross-cutting | А01 (note) |

---

## Usage Instructions

1. **Select** the definitions relevant to the specific prompt's task.
2. **Copy** the definition block (everything inside the ``` markers) into the prompt text.
3. **Do not paraphrase** — the tests and examples are calibrated to prevent specific classification errors observed in practice.
4. For Level 2A prompts (venue structure), always include DEF-A02, DEF-A05, DEF-A04, and DEF-G08 together — they form a classification system that only works as a set.
5. For Level 3 prompts (cell analysis), always include DEF-G01 and DEF-V04.

---

*This document is a supplement to Conceptual Core v0. DEF-G08 (Admission Regime Modifier) is a new concept not present in v0 and should be added to the core in v1.*
