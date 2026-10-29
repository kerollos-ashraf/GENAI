import pytest

from app.rag.chunker import Chunker
from tests.conftest import POLICY

WATER = "sample_policy.md § Section 1: Home Water Damage Coverage"
PROPERTY = "sample_policy.md § Section 2: Personal Property Protection"


def test_policy_is_chunked_by_section_with_citations():
    chunks = Chunker().chunk(POLICY.name, POLICY.read_bytes())
    assert [c.metadata["citation"] for c in chunks] == [WATER, PROPERTY]
    assert "$25,000" in chunks[0].page_content
    assert "$10,000" in chunks[1].page_content


@pytest.mark.parametrize(
    "query, expected",
    [
        ("Is a burst pipe covered?", WATER),
        ("What is the deductible for water damage?", WATER),
        ("Are floods covered?", WATER),
        ("Is my jewelry covered?", PROPERTY),
        ("Do I need an appraisal receipt for an expensive laptop item?", PROPERTY),
        ("What is the limit for electronics and furniture?", PROPERTY),
    ],
)
def test_retrieval_ranks_the_right_section_first(retriever, query, expected):
    results = retriever.search(query, k=2)
    assert results[0].citation == expected
    assert results[0].score >= results[-1].score


def test_resync_is_idempotent(retriever):
    report = retriever.sync()
    assert report.unchanged == ["sample_policy.md"] and not report.changed
    retriever.sync(force=True)
    assert retriever.index.count() == 2
