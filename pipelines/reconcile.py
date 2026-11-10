"""Compare the seed hierarchy with the project's Consolidated Master v3.0 (Rajshahi Division).

The master is a reconciliation source, not an authority: it marks every union non-production.
This module never changes the seed. It reports where the two agree, where they differ, and
whether each difference is a known, tracked conflict (refdata.KNOWN_MASTER_DIFFS).
"""
import csv, difflib, os, re
from trust import nfc

MASTER = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sources", "master_v3")

# Per-district file holding the master's selected per-upazila union counts, and which column to use.
UPAZILA_COUNTS = {
    "Rajshahi": ("rajshahi_district_reconciliation/rajshahi_upazila_distribution_baseline.csv", "selected_union_count"),
    "Natore": ("natore_reconciliation/natore_upazila_count_reconciliation.csv", "district_admin_current_count"),
    "Naogaon": ("naogaon_reconciliation/naogaon_upazila_count_reconciliation.csv", "official_district_page_visible_count"),
    "Chapainawabganj": ("chapainawabganj_reconciliation/chapainawabganj_upazila_count_reconciliation.csv", "selected_target_union_count"),
    "Bogura": ("bogura_reconciliation/bogura_upazila_distribution_baseline.csv", "historical_selected_union_count"),
    "Joypurhat": ("joypurhat_reconciliation/joypurhat_upazila_count_reconciliation.csv", "official_district_portal_count_2024"),
    "Pabna": ("pabna_reconciliation/pabna_upazila_distribution_baseline.csv", "secondary_73_distribution"),
    "Sirajganj": ("sirajganj_reconciliation/sirajganj_upazila_distribution_baseline.csv", "selected_union_count"),
}

# Registers that carry individual union names.
NAMED_REGISTERS = {
    "Joypurhat": "joypurhat_reconciliation/joypurhat_32_union_candidate_master.csv",
    "Naogaon": "naogaon_reconciliation/naogaon_99_union_candidate_master.csv",
    "Natore": "natore_reconciliation/natore_52_union_candidate_master.csv",
    "Chapainawabganj": "chapainawabganj_reconciliation/chapainawabganj_45_union_candidate_register.csv",
    "Rajshahi": "rajshahi_v1_7/rajshahi_72_candidate_master.csv",
}

# Spelling differences between nuhil (seed) and master upazila names.
UPAZILA_ALIASES = {
    "bogra sadar": "bogura sadar", "nondigram": "nandigram", "dhunot": "dhunat", "shariakandi": "sariakandi",
    "dupchanchia": "dhupchanchia", "mohonpur": "mohanpur", "gomostapur": "gomastapur", "badalgachi": "badalgachhi",
    "ishurdi": "ishwardi", "kamarkhand": "kamarkhanda", "raigonj": "raiganj", "shajahanpur": "shajahanpur",
}


def latin_key(s):
    """Python twin of packages/shared/src/search.ts latinKey()."""
    s = (s or "").lower()
    s = re.sub(r"[^a-z0-9]+", "", s)
    for a, b in (("sh", "s"), ("oo", "u"), ("ou", "u"), ("ee", "i"), ("ii", "i"), ("aa", "a"), ("w", "o")):
        s = s.replace(a, b)
    return re.sub(r"([a-z])\1+", r"\1", s)


def upazila_key(name):
    n = (name or "").strip().lower()
    return latin_key(UPAZILA_ALIASES.get(n, n))


def bn_key(s):
    return re.sub(r"[\s\-\(\)\.,]", "", nfc(s or ""))


def variant_score(m, s):
    a, b = latin_key(m.get("union_en")), latin_key(s["name_en"])
    if a and b and (a.startswith(b) or b.startswith(a) or a.endswith(b) or b.endswith(a)):
        return 0.9
    r1 = difflib.SequenceMatcher(None, a, b).ratio()
    r2 = difflib.SequenceMatcher(None, bn_key(m.get("union_bn")), bn_key(s["name_bn"])).ratio() if m.get("union_bn") else 0.0
    return max(r1, r2)


def read(rel):
    with open(os.path.join(MASTER, rel), encoding="utf-8-sig", newline="") as f:
        return [{k: nfc(v) for k, v in r.items()} for r in csv.DictReader(f)]


def master_counts():
    out = {}
    for district, (rel, col) in UPAZILA_COUNTS.items():
        for r in read(rel):
            if not (r.get("upazila_en") or "").strip():
                continue
            v = (r.get(col) or "").strip()
            out[(district, upazila_key(r["upazila_en"]))] = dict(upazila=r["upazila_en"], count=int(v) if v.isdigit() else None,
                                                                 basis=f"{rel}:{col}")
    return out


def compare(rows, known):
    """rows: seed admin_areas rows (after fixes). known: refdata.KNOWN_MASTER_DIFFS.
    Returns (upazila_rows, name_rows, district_rows)."""
    by_id = {r["id"]: r for r in rows}
    districts = {r["name_en"]: r for r in rows if r["level"] == "district" and r["name_en"] in UPAZILA_COUNTS}
    upz = {}
    for r in rows:
        if r["level"] == "upazila" and by_id[r["parent_id"]]["name_en"] in districts:
            upz[(by_id[r["parent_id"]]["name_en"], upazila_key(r["name_en"]))] = r
    unions = {}
    for r in rows:
        if r["level"] == "union" and r["parent_id"] in by_id and by_id[r["parent_id"]]["level"] == "upazila":
            unions.setdefault(r["parent_id"], []).append(r)

    mc = master_counts()
    used = set()

    def status(key):
        return ("known", known[key]) if key in known else ("UNTRACKED", "")

    upazila_rows = []
    for (district, k), u in sorted(upz.items(), key=lambda x: (x[0][0], x[1]["name_en"])):
        m = mc.get((district, k))
        used.add((district, k))
        seed_n = len(unions.get(u["id"], []))
        m_n = m["count"] if m else None
        st, note = ("match", "") if m_n == seed_n else status(("count", district, u["name_en"]))
        upazila_rows.append(dict(district=district, upazila_seed=u["name_en"], upazila_master=m["upazila"] if m else "",
                                 seed_unions=seed_n, master_unions="" if m_n is None else m_n,
                                 master_basis=m["basis"] if m else "", status=st, note=note))
    for (district, k), m in sorted(mc.items()):
        if (district, k) not in used:
            st, note = status(("count", district, m["upazila"]))
            upazila_rows.append(dict(district=district, upazila_seed="", upazila_master=m["upazila"], seed_unions="",
                                     master_unions=m["count"], master_basis=m["basis"], status=st, note=note))

    name_rows = []
    for district, rel in NAMED_REGISTERS.items():
        reg = [r for r in read(rel) if (r.get("union_en") or r.get("union_bn") or "").strip()]
        by_upz = {}
        for r in reg:
            by_upz.setdefault(upazila_key(r["upazila_en"]), []).append(r)
        for k, mrows in sorted(by_upz.items()):
            u = upz.get((district, k))
            seed = list(unions.get(u["id"], [])) if u else []
            upz_name = u["name_en"] if u else mrows[0]["upazila_en"]
            unmatched_seed = seed[:]
            unmatched_master = []
            for m in mrows:
                hit = None
                for s in unmatched_seed:
                    if (m.get("union_bn") and bn_key(m["union_bn"]) == bn_key(s["name_bn"])) or \
                       latin_key(m.get("union_en")) == latin_key(s["name_en"]) or \
                       difflib.SequenceMatcher(None, latin_key(m.get("union_en")), latin_key(s["name_en"])).ratio() >= 0.85:
                        hit = s
                        break
                if hit:
                    unmatched_seed.remove(hit)
                else:
                    unmatched_master.append(m)
            # second pass: pair remaining names that are spelling variants of each other
            for m in list(unmatched_master):
                best, score = None, 0.0
                for s in unmatched_seed:
                    sc = variant_score(m, s)
                    if sc > score:
                        best, score = s, sc
                if best is not None and score >= 0.7:
                    unmatched_master.remove(m)
                    unmatched_seed.remove(best)
                    name_rows.append(dict(district=district, upazila=upz_name, side="spelling_variant",
                                          union_en=f"{m.get('union_en', '')} | seed: {best['name_en']}",
                                          union_bn=f"{m.get('union_bn', '')} | seed: {best['name_bn']}", status="variant",
                                          note=f"similarity {score:.2f}"))
            for m in unmatched_master:
                st, note = status(("name", district, upz_name, "master_only", m.get("union_en", "")))
                name_rows.append(dict(district=district, upazila=upz_name, side="master_only", union_en=m.get("union_en", ""),
                                      union_bn=m.get("union_bn", ""), status=st, note=note))
            for s in unmatched_seed:
                st, note = status(("name", district, upz_name, "seed_only", s["name_en"]))
                name_rows.append(dict(district=district, upazila=upz_name, side="seed_only", union_en=s["name_en"],
                                      union_bn=s["name_bn"], status=st, note=note))

    cross = {r["district_en"]: r for r in read("regional_baseline/rajshahi_division_union_count_crosswalk.csv")}
    district_rows = []
    for name, d in sorted(districts.items()):
        seed_n = sum(len(unions.get(u["id"], [])) for (dn, _), u in upz.items() if dn == name)
        c = cross.get(name, {})
        district_rows.append(dict(district=name, seed_unions=seed_n, master_selected_2026=c.get("selected_current_union_count_2026", ""),
                                  bbs_2011=c.get("bbs_union_count_2011", ""), note=c.get("reconciliation_note", "")))
    return upazila_rows, name_rows, district_rows


def conflicts():
    """Flatten every master conflict register into one table."""
    out = []
    for root, _, files in os.walk(MASTER):
        for fn in sorted(files):
            if not fn.endswith("conflict_register.csv"):
                continue
            rel = os.path.relpath(os.path.join(root, fn), MASTER)
            district = fn.split("_")[0].capitalize()
            for r in read(rel):
                cid = r.pop("conflict_id", "")
                topic = r.pop("topic", None) or r.pop("subject", "")
                st = r.pop("status", "")
                claims = "; ".join(f"{k}: {v}" for k, v in r.items() if v)
                out.append(dict(conflict_id=cid, district=district, topic=topic, status=st, detail=claims, source_file=f"master_v3/{rel}"))
    return sorted(out, key=lambda r: (r["district"], r["conflict_id"]))
