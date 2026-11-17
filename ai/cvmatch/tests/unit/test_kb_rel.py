from cvmatch.core.config import load_config
from cvmatch.core.kb.rel import RoleDistance, SkillRelations

JAVA, SPRING_BOOT, PYTHON, POSTGRES, MYSQL = "S0001", "S0002", "S0009", "S0015", "S0016"
REACT, VUE, KAFKA, RABBIT = "S0006", "S0032", "S0021", "S0022"


def test_rel_values(kb_mini):
    r = SkillRelations.from_config(kb_mini, load_config().rerank.rel)
    assert r.rel(JAVA, JAVA) == 1.0
    assert r.rel(SPRING_BOOT, JAVA) == 0.7 and r.relation(SPRING_BOOT, JAVA) == "child"
    assert r.relation(JAVA, SPRING_BOOT) == "parent"
    assert r.rel(MYSQL, POSTGRES) == 0.4               # chung Category sibling_ok
    assert r.rel(REACT, VUE) == 0.4                    # chung cha JavaScript
    assert r.rel(KAFKA, RABBIT) == 0.4
    assert r.rel(PYTHON, JAVA) == 0.0


def test_role_distance(kb_mini):
    m = RoleDistance(kb_mini)
    assert m("Backend", "Backend") == 1.0
    assert m("Backend", "Fullstack") == m("Fullstack", "Backend") == 0.8
    assert m("QA", "Backend") == 0.2
    assert m("Mobile", "Security") == 0.0
    assert m(None, "Backend") is None
