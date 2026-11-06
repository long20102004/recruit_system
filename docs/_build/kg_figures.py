"""Export KG figures from the live Neo4j for the report (no CV data involved)."""
import os
import sys

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx
from neo4j import GraphDatabase

out = sys.argv[1]
drv = GraphDatabase.driver("bolt://localhost:7687", auth=("neo4j", os.environ["NEO4J_PASSWORD"]))
plt.rcParams["font.family"] = "DejaVu Sans"

with drv.session() as s:
    labels = {r["l"]: r["n"] for r in s.run("MATCH (n) UNWIND labels(n) AS l RETURN l, count(*) AS n")}
    rels = {r["t"]: r["n"] for r in s.run("MATCH ()-[r]->() RETURN type(r) AS t, count(*) AS n")}
    rels["SKILL_ALIAS"] = s.run("MATCH (:Alias)-[r:ALIAS_OF]->(:Skill) RETURN count(r) AS n").single()["n"]
    rels["UNI_ALIAS"] = s.run("MATCH (:UniversityAlias)-[r:ALIAS_OF]->(:University) RETURN count(r) AS n").single()["n"]

    # ---- figure 1: schema (meta graph) ----
    G = nx.MultiDiGraph()
    meta = [("Alias", "Skill", "SKILL_ALIAS"), ("Skill", "Category", "IN_CATEGORY"), ("Skill", "Skill", "REQUIRES / PART_OF"),
            ("Skill", "Skill", "RELATED_TO"), ("UniversityAlias", "University", "UNI_ALIAS"),
            ("Book", "Section", "HAS_SECTION"), ("Section", "Skill", "MENTIONS / ABOUT")]
    pos = {"Book": (-2.2, 1.2), "Section": (-0.6, 1.2), "Skill": (0.9, 0.2), "Alias": (2.5, 1.1), "Category": (2.5, -0.7),
           "University": (-0.6, -1.2), "UniversityAlias": (-2.2, -1.2), "JobTitle": (2.5, -1.6)}
    color = {"Book": "#F4B183", "Section": "#F4B183", "Skill": "#9DC3E6", "Alias": "#DEEBF7", "Category": "#DEEBF7",
             "University": "#A9D18E", "UniversityAlias": "#E2F0D9", "JobTitle": "#D9D9D9"}
    fig, ax = plt.subplots(figsize=(10, 5.6))
    for a, b, lab in meta:
        if a == b:
            ax.annotate("", xy=(pos[a][0] + 0.25, pos[a][1] + 0.18), xytext=(pos[a][0] - 0.25, pos[a][1] + 0.18),
                        arrowprops=dict(arrowstyle="->", connectionstyle="arc3,rad=-1.6", color="#404040"))
            ax.text(pos[a][0], pos[a][1] + 0.62 if "REQ" in lab else pos[a][1] + 0.85, lab + f"\n({rels.get('REQUIRES',0)+rels.get('PART_OF',0) if 'REQ' in lab else rels.get('RELATED_TO',0)})",
                    ha="center", fontsize=8, color="#2E75B6" if "RELATED" in lab else "#404040")
            continue
        ax.annotate("", xy=pos[b], xytext=pos[a], arrowprops=dict(arrowstyle="->", color="#404040", shrinkA=34, shrinkB=34))
        mx, my = (pos[a][0] + pos[b][0]) / 2, (pos[a][1] + pos[b][1]) / 2
        n = rels.get(lab.split(" /")[0], 0) + (rels.get("ABOUT", 0) if "ABOUT" in lab else 0)
        shown = {"SKILL_ALIAS": "ALIAS_OF", "UNI_ALIAS": "ALIAS_OF"}.get(lab, lab)
        ax.text(mx, my + 0.08, f"{shown} ({n})", ha="center", fontsize=8, color="#404040")
    for node, (x, y) in pos.items():
        ax.text(x, y, f"{node}\n{labels.get(node, 0)}", ha="center", va="center", fontsize=9, fontweight="bold",
                bbox=dict(boxstyle="round,pad=0.5", fc=color[node], ec="#595959"))
    ax.text(-2.2, 1.85, "KB1 — sách PDF", ha="center", fontsize=10, color="#C55A11", fontweight="bold")
    ax.text(1.7, 1.85, "KB2 — nguồn liên kết (Stack Overflow, Wikidata, ESCO, Linguist, Wikipedia)", ha="center", fontsize=10, color="#1F4E79", fontweight="bold")
    ax.set_xlim(-3, 3.3); ax.set_ylim(-2.1, 2.1); ax.axis("off")
    fig.tight_layout(); fig.savefig(f"{out}/kg_schema.png", dpi=170); plt.close(fig)

    # ---- figure 2: real subgraph ----
    seeds = ["Spring Boot", "React", "Git", "Python", "Hibernate", "Express"]
    H = nx.MultiDiGraph()
    for r in s.run("""MATCH (a:Skill)-[r:REQUIRES|PART_OF]->(b:Skill) WHERE a.name IN $seeds
                      RETURN a.name AS a, type(r) AS t, b.name AS b""", seeds=seeds):
        H.add_edge(r["a"], r["b"], t=r["t"])
    for r in s.run("""MATCH (a:Skill)-[r:RELATED_TO]-(b:Skill) WHERE a.name IN ['Git','Python'] AND r.weight >= 9
                      RETURN a.name AS a, b.name AS b, r.weight AS w ORDER BY w DESC LIMIT 9""", seeds=seeds):
        if not H.has_edge(r["b"], r["a"]):
            H.add_edge(r["a"], r["b"], t="RELATED_TO", w=r["w"])
    book_nodes = set()
    for r in s.run("""MATCH (bk:Book)-[:HAS_SECTION]->(c:Section)-[:HAS_SECTION]->(sec:Section)-[m:MENTIONS]->(k:Skill)
                      WHERE k.name IN ['Git','Python'] AND m.count >= 25
                      RETURN bk.title AS book, c.title AS ch, sec.title AS sec, k.name AS k, m.count AS n
                      ORDER BY n DESC LIMIT 4"""):
        bk = r["book"].split(":")[0][:22]
        sec = "§ " + r["sec"][:26]
        H.add_edge(bk, sec, t="HAS_SECTION"); H.add_edge(sec, r["k"], t="MENTIONS", w=r["n"])
        book_nodes |= {bk, sec}
    pos = nx.spring_layout(nx.Graph(H), seed=7, k=1.1)
    fig, ax = plt.subplots(figsize=(11, 7))
    style = {"REQUIRES": ("#1F4E79", "solid"), "PART_OF": ("#7030A0", "dashed"), "RELATED_TO": ("#548235", "solid"),
             "MENTIONS": ("#C55A11", "dotted"), "HAS_SECTION": ("#A6A6A6", "solid")}
    for t, (c, ls) in style.items():
        es = [(u, v) for u, v, d in H.edges(data=True) if d["t"] == t]
        nx.draw_networkx_edges(H, pos, edgelist=es, edge_color=c, style=ls, arrows=True, arrowsize=12, width=1.6, ax=ax,
                               connectionstyle="arc3,rad=0.06")
    el = {(u, v): (d["t"] if d["t"] != "RELATED_TO" else f"RELATED_TO ({int(d['w'])})") for u, v, d in H.edges(data=True)
          if d["t"] in ("REQUIRES", "PART_OF", "RELATED_TO")}
    nx.draw_networkx_edge_labels(H, pos, edge_labels=el, font_size=6.5, ax=ax, rotate=False)
    ncol = ["#F4B183" if n in book_nodes else ("#2E75B6" if n in seeds else "#9DC3E6") for n in H.nodes]
    nx.draw_networkx_nodes(H, pos, node_color=ncol, node_size=[2300 if n in seeds else 1500 for n in H.nodes], ax=ax, edgecolors="#404040")
    nx.draw_networkx_labels(H, pos, font_size=7.5, ax=ax, font_color="black")
    handles = [plt.Line2D([0], [0], color=c, ls=ls, lw=2, label=t) for t, (c, ls) in style.items()]
    ax.legend(handles=handles, loc="lower left", fontsize=8, frameon=True)
    ax.axis("off"); fig.tight_layout(); fig.savefig(f"{out}/kg_subgraph.png", dpi=170); plt.close(fig)
drv.close()
print("figures written", labels.get("Skill"), rels)
