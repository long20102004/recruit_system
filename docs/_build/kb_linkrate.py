"""Link rate of gold skills / schools of the 20 real test CVs against a KB seed dir (counts only)."""
import json, sys
sys.path.insert(0, ".")
from app.kb.store import KnowledgeBase
from app.postprocess.skills import clean_skill_list
kb = KnowledgeBase.from_csv(sys.argv[1])
rows = [json.loads(l) for l in open("data/retrain_v3/test_real.jsonl")]
s_tot = s_link = sc_tot = sc_link = 0; meth = {}
for r in rows:
    g = json.loads(r["output"])
    skills = clean_skill_list(g.get("skills") or [])
    for raw in skills:
        links = kb.linker.link_many([raw])
        s_tot += 1
        ok = bool(links) and all(l.skill_id is not None for l in links)
        s_link += ok
        for l in links: meth[l.method] = meth.get(l.method, 0) + 1
    for e in g.get("education") or []:
        if e.get("school"):
            sc_tot += 1; sc_link += kb.link_school(e["school"]) is not None
print(f"KB={sys.argv[1].split('/')[-3] if 'oldkb' in sys.argv[1] else sys.argv[1]} skills {len(kb.skills)} | gold skills linked {s_link}/{s_tot} = {s_link/s_tot:.3f} | methods {meth} | schools linked {sc_link}/{sc_tot} = {sc_link/sc_tot:.3f}")
