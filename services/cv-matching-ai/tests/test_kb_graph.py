from app.features import score_skill_pair
from app.graph import default_skill_graph, direct_relation, skill_to_node_id, skills_for_title


def test_spring_boot_requires_java_and_a_job_title_names_java():
    graph = default_skill_graph()
    spring = skill_to_node_id("Spring Boot")
    java = skill_to_node_id("Java")
    assert direct_relation(graph, spring, java) == "REQUIRES"
    assert score_skill_pair(graph, "Spring Boot", "Java") == 0.8
    assert "Java" in skills_for_title("Junior Backend Developer (Java)")
