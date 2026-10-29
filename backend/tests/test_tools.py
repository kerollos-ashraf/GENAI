import json
from concurrent.futures import ThreadPoolExecutor

import pytest
from pydantic import ValidationError

from app.agent.tools import AssistantToolkit
from app.domain.claims import ClaimNotFoundError, ClaimSubmission

VALID = {
    "policy_number": "POL-1092",
    "claim_type": "Water Damage",
    "amount": 4200.5,
    "description": "Kitchen pipe burst overnight and flooded the floor.",
}


@pytest.fixture
def tools(retriever, claims_repo):
    return {t.name: t for t in AssistantToolkit(retriever, claims_repo, top_k=2).tools()}


# --- get_claim_status -------------------------------------------------------------------


def test_get_claim_status_returns_record(tools):
    out = json.loads(tools["get_claim_status"].invoke({"claim_id": "CLM-8821"}))
    assert out["status"] == "Approved"
    assert out["amount"] == 3500.0


def test_get_claim_status_normalises_id(tools):
    out = json.loads(tools["get_claim_status"].invoke({"claim_id": "  clm-9014 "}))
    assert out["status"] == "Under Review"


def test_get_claim_status_unknown_claim(tools):
    assert "No claim found" in tools["get_claim_status"].invoke({"claim_id": "CLM-0000"})


@pytest.mark.parametrize("bad", ["8821", "CLM-12", "CLM-8821; DROP TABLE", ""])
def test_get_claim_status_rejects_malformed_ids(tools, bad):
    with pytest.raises(ValidationError):
        tools["get_claim_status"].invoke({"claim_id": bad})


def test_repository_raises_for_missing(claims_repo):
    with pytest.raises(ClaimNotFoundError):
        claims_repo.get("CLM-1111")


# --- submit_claim -----------------------------------------------------------------------


def test_submit_claim_appends_record_and_returns_confirmation(tools, claims_file):
    out = tools["submit_claim"].invoke(VALID)
    assert "Confirmation ID: CLM-" in out

    records = json.loads(claims_file.read_text())
    assert len(records) == 3
    new = records[-1]
    assert new["status"] == "Submitted"
    assert new["policy_number"] == "POL-1092"
    assert new["amount"] == 4200.5
    assert new["claim_id"] in out


def test_submitted_claim_can_be_looked_up(tools):
    out = tools["submit_claim"].invoke(VALID)
    claim_id = out.split("Confirmation ID: ")[1].split(".")[0]
    assert (
        json.loads(tools["get_claim_status"].invoke({"claim_id": claim_id}))["status"]
        == "Submitted"
    )


def test_submit_claim_normalises_aliases():
    sub = ClaimSubmission(**{**VALID, "policy_number": "pol-1092", "claim_type": "water"})
    assert sub.policy_number == "POL-1092"
    assert sub.claim_type == "Water Damage"


@pytest.mark.parametrize(
    "override",
    [
        {"policy_number": "1092"},
        {"claim_type": "Car Theft"},
        {"amount": -50},
        {"amount": 0},
        {"amount": "lots"},
        {"amount": float("inf")},
        {"amount": 5_000_000},
        {"description": "short"},
    ],
)
def test_submit_claim_rejects_invalid_input(tools, claims_file, override):
    with pytest.raises(ValidationError):
        tools["submit_claim"].invoke({**VALID, **override})
    assert len(json.loads(claims_file.read_text())) == 2  # nothing written


def test_concurrent_submissions_are_all_persisted(claims_repo, claims_file):
    with ThreadPoolExecutor(max_workers=8) as pool:
        ids = list(
            pool.map(lambda _: claims_repo.submit(ClaimSubmission(**VALID)).claim_id, range(20))
        )
    assert len(set(ids)) == 20
    assert len(json.loads(claims_file.read_text())) == 22


# --- search_policy ----------------------------------------------------------------------


def test_search_policy_returns_cited_passages(tools):
    msg = tools["search_policy"].invoke(
        {"type": "tool_call", "id": "1", "name": "search_policy", "args": {"query": "burst pipe"}}
    )
    assert "[sample_policy.md § Section 1: Home Water Damage Coverage]" in msg.content
    assert msg.artifact[0] == "sample_policy.md § Section 1: Home Water Damage Coverage"
