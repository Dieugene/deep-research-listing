"""Quantitative audit: raw basis vs pipeline result for sources/excerpts.

Sources with excerpts_joined=true are counted separately —
their excerpt count differs from basis by design (fragments joined into 1).
"""
import json
from pathlib import Path

data = Path("03_data/countries")


def count_basis(filepath):
    """Count citations and excerpts in parallel_output.basis."""
    if not filepath.exists():
        return 0, 0
    with open(filepath, encoding="utf-8") as f:
        d = json.load(f)
    basis = d.get("parallel_output", {}).get("basis", [])
    cits = 0
    excs = 0
    for b in basis:
        for c in b.get("citations", []):
            cits += 1
            excs += len(c.get("excerpts", []))
    return cits, excs


def count_sources(filepath, key="sources"):
    """Count sources/citations and excerpts in derived file.

    Returns (citations, excerpts_non_joined, joined_count).
    joined_count = number of sources with excerpts_joined=true.
    """
    if not filepath.exists():
        return 0, 0, 0
    with open(filepath, encoding="utf-8") as f:
        d = json.load(f)
    srcs = d.get(key, [])
    cits = len(srcs)
    excs = 0
    joined = 0
    for s in srcs:
        if s.get("excerpts_joined"):
            joined += 1
        else:
            excs += len(s.get("excerpts", []))
    return cits, excs, joined


# =========================================================================
print("=" * 100)
print("LEVEL 1: 1A + 1B + 1C basis -> jurisdiction_card.json sources")
print("=" * 100)
print(f"{'Jurisdiction':<20} | {'basis_cit':>10} {'basis_exc':>10} | {'result_cit':>10} {'res_exc':>10} {'joined':>7} | {'d_cit':>6} {'d_exc':>7}")
print("-" * 100)

t1_bc, t1_be, t1_rc, t1_re, t1_rj = 0, 0, 0, 0, 0
for jur in sorted(data.iterdir()):
    if not jur.is_dir():
        continue
    bc, be = 0, 0
    for fname in ["1A_architecture.json", "1B_institutional.json", "1C_venues.json"]:
        c, e = count_basis(jur / "level_1" / fname)
        bc += c
        be += e
    rc, re_, rj = count_sources(jur / "level_1" / "jurisdiction_card.json")
    dc = rc - bc
    de = re_ - be  # will be negative due to joined excerpts not counted
    de_note = f"{de:>+7}" if rj == 0 else f"{de:>+5}+J"
    print(f"{jur.name:<20} | {bc:>10} {be:>10} | {rc:>10} {re_:>10} {rj:>7} | {dc:>+6} {de_note}")
    t1_bc += bc
    t1_be += be
    t1_rc += rc
    t1_re += re_
    t1_rj += rj
print("-" * 100)
t1_de_note = f"{t1_re-t1_be:>+5}+J" if t1_rj else f"{t1_re-t1_be:>+7}"
print(f"{'TOTAL L1':<20} | {t1_bc:>10} {t1_be:>10} | {t1_rc:>10} {t1_re:>10} {t1_rj:>7} | {t1_rc-t1_bc:>+6} {t1_de_note}")
print(f"  ({t1_rj} sources had excerpts joined by LLM — their fragment count excluded from comparison)")

# =========================================================================
print()
print("=" * 100)
print("LEVEL 2: 2A_structure + venue_card basis -> venue_card.json sources")
print("=" * 100)

t2_bc, t2_be, t2_rc, t2_re = 0, 0, 0, 0
for jur in sorted(data.iterdir()):
    if not jur.is_dir():
        continue
    l2 = jur / "level_2"
    if not l2.exists():
        continue
    for venue in sorted(l2.iterdir()):
        if not venue.is_dir():
            continue
        bc1, be1 = count_basis(venue / "2A_structure.json")
        bc2, be2 = count_basis(venue / "venue_card.json")
        bc = bc1 + bc2
        be = be1 + be2
        rc, re_, _ = count_sources(venue / "venue_card.json")
        t2_bc += bc
        t2_be += be
        t2_rc += rc
        t2_re += re_

print(f"TOTAL L2: basis={t2_bc} cit, {t2_be} exc | result={t2_rc} cit, {t2_re} exc | delta={t2_rc-t2_bc:+d} cit, {t2_re-t2_be:+d} exc")

# =========================================================================
print()
print("=" * 100)
print("LEVEL 3: 3A/3B/3C basis -> citations[] (in _parallel_raw)")
print("=" * 100)
print(f"{'Jurisdiction':<20} | {'basis_cit':>10} {'basis_exc':>10} | {'cit[]_cit':>10} {'cit[]_exc':>10} {'joined':>7}")
print("-" * 100)

t3_bc, t3_be = 0, 0
t3_cc, t3_ce, t3_cj = 0, 0, 0

for jur in sorted(data.iterdir()):
    if not jur.is_dir():
        continue
    l3 = jur / "level_3"
    if not l3.exists():
        continue
    jbc, jbe = 0, 0
    jcc, jce, jcj = 0, 0, 0
    for venue in sorted(l3.iterdir()):
        if not venue.is_dir():
            continue
        par_raw = venue / "_parallel_raw"
        if not par_raw.exists():
            continue
        for rp in sorted(par_raw.glob("*_raw.json")):
            if "_tier_map" in rp.name:
                continue
            bc, be = count_basis(rp)
            jbc += bc
            jbe += be
            cc, ce, cj = count_sources(rp, key="citations")
            jcc += cc
            jce += ce
            jcj += cj

    print(f"{jur.name:<20} | {jbc:>10} {jbe:>10} | {jcc:>10} {jce:>10} {jcj:>7}")
    t3_bc += jbc
    t3_be += jbe
    t3_cc += jcc
    t3_ce += jce
    t3_cj += jcj

print("-" * 100)
print(f"{'TOTAL L3':<20} | {t3_bc:>10} {t3_be:>10} | {t3_cc:>10} {t3_ce:>10} {t3_cj:>7}")
pct_cit = 100 * t3_cc / t3_bc if t3_bc else 0
print(f"  basis -> citations[]: {pct_cit:.0f}%")
print(f"  ({t3_cj} sources had excerpts joined by LLM)")

# =========================================================================
print()
print("=" * 100)
print("LEVEL 4: 4A_raw.json basis -> level4.json sources")
print("=" * 100)

t4_bc, t4_be, t4_rc, t4_re = 0, 0, 0, 0
for jur in sorted(data.iterdir()):
    if not jur.is_dir():
        continue
    bc, be = count_basis(jur / "level_4" / "4A_raw.json")
    rc, re_, _ = count_sources(jur / "level_4" / "level4.json")
    print(f"{jur.name:<20} | basis: {bc:>4} ({be:>4} exc) | result: {rc:>4} ({re_:>4} exc) | delta: {rc-bc:+d}")
    t4_bc += bc
    t4_be += be
    t4_rc += rc
    t4_re += re_
print("-" * 100)
print(f"{'TOTAL L4':<20} | basis: {t4_bc:>4} ({t4_be:>4} exc) | result: {t4_rc:>4} ({t4_re:>4} exc) | delta: {t4_rc-t4_bc:+d}")

# =========================================================================
print()
print("=" * 100)
print("GRAND TOTAL (excerpts: non-joined only)")
print("=" * 100)
gb = t1_bc + t2_bc + t3_bc + t4_bc
ge = t1_be + t2_be + t3_be + t4_be
gr = t1_rc + t2_rc + t3_cc + t4_rc
gre = t1_re + t2_re + t3_ce + t4_re
gj = t1_rj + t3_cj
print(f"  Raw (basis):      {gb:>6} citations,  {ge:>6} excerpts")
print(f"  Pipeline result:  {gr:>6} citations,  {gre:>6} excerpts (non-joined)")
print(f"  Joined sources:   {gj:>6} (excerpt count reduced by design)")
if gb:
    print(f"  Retention cit:    {100*gr/gb:.1f}%")
if ge:
    print(f"  Retention exc:    {100*gre/(ge):.1f}% (of non-joined; joined excluded from both sides)")
