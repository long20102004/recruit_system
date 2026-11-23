import numpy as np

from app.retrieval import hybrid_retrieve


def test_hybrid_retrieve_returns_top_k_in_relevance_order():
    candidates = [
        {"id": "irrelevant", "text": "accounting finance"},
        {"id": "relevant", "text": "python fastapi backend"},
        {"id": "partial", "text": "python data"},
    ]

    def embed(text):
        text = text.lower()
        return np.array(
            [
                float("python" in text),
                float("fastapi" in text),
                float("backend" in text),
            ]
        )

    results = hybrid_retrieve("python fastapi backend", candidates, embed_fn=embed, top_k=2)

    assert len(results) == 2
    assert results[0]["id"] == "relevant"
    assert "retrieval_score" in results[0]
