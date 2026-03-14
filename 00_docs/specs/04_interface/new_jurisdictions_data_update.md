# New Jurisdictions Data Update

**Date:** 2026-03-14

## What was added

Two additional pipeline runs completed. Four new jurisdictions are now in the database:

| Jurisdiction | Venues |
|---|---|
| Австралия (Australia) | ASX, Cboe Australia, NSX, SSX |
| Сингапур (Singapore) | SGX Mainboard and Catalist |
| Франция (France) | Euronext Paris, Euronext Growth Paris, Euronext Access Paris, MTS France, Aquis Exchange Europe |
| Германия (Germany) | Frankfurt Stock Exchange, Tradegate, Berlin Stock Exchange, Börse Stuttgart, Börse München, BÖAG Börsen (Düsseldorf/Hamburg/Hannover) |

## Data structure (same as existing jurisdictions)

```
03_data/countries/{name_ru}/
  level_1/                          — jurisdiction_card.json, venues_list.json
  level_2/{venue_key}/              — venue_card.json
  level_3/{venue_key}/{cell_id}/    — admission / maintenance / enforcement text
  level_4/                          — level4.json, level4_validation.json
```

## L4 validation — all GREEN

| Jurisdiction | Problems | Contradictions | Params | Reforms |
|---|---|---|---|---|
| Франция | 4 | 3 | 5 | 3 |
| Германия | 7 | 5 | 6 | 5 |

(Австралия and Сингапур validated in prior run — also GREEN.)

## Frontend fix already applied — Reform.year field

`level4.json` Reform objects use `year` (not `period` like Problems/Contradictions/Parameters). This was a pre-existing data model inconsistency. Already fixed:

- `types.ts` — `Level4Item` interface now includes `year?: string`
- `JurisdictionPage.tsx` — date display uses `item.period || item.year`

No data re-processing needed.

## What you need to do

Nothing. The backend reads jurisdictions dynamically from the filesystem. The four new jurisdictions will appear via the existing `/api/jurisdictions` endpoint after a backend restart. No schema changes, no migrations.
