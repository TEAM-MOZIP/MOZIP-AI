import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.ontology.loader import _load_graph, get_ontology_graph
from app.schemas.mapping import UserMappingInput
from app.schemas.semantic_match_api import SemanticMatchBatchPolicyItem, SemanticMatchBatchRequest

FIXTURE_PATH = "app/tests/fixtures/test_user_mapping_ontology.ttl"
ENDPOINT = "/api/v1/semantic-match/batch"


@pytest.fixture(autouse=True)
def _override_ontology_graph():
    graph = _load_graph(FIXTURE_PATH)
    app.dependency_overrides[get_ontology_graph] = lambda: graph
    yield
    app.dependency_overrides.pop(get_ontology_graph, None)


client = TestClient(app)


def _payload(policies: list[dict]) -> dict:
    return {
        "user": {
            "gender": "MALE",
            "regionCode": "SEOUL_GANGNAM",
            "employmentStatus": "JOB_SEEKER",
        },
        "policies": policies,
    }


def test_batch_endpoint_returns_200_with_camel_case_contract():
    response = client.post(
        ENDPOINT,
        json=_payload(
            [
                {
                    "policyId": 101,
                    "regionScope": "REGIONAL",
                    "regionCodes": ["SEOUL"],
                    "allowedEmploymentStatuses": ["JOB_SEEKER"],
                }
            ]
        ),
    )

    assert response.status_code == 200
    body = response.json()
    [result] = body["results"]

    assert result["policyId"] == 101
    assert result["semanticScore"] is not None
    assert set(result.keys()) == {
        "policyId",
        "semanticScore",
        "matchedConcepts",
        "inferencePaths",
    }

    matched_region = next(m for m in result["matchedConcepts"] if m["axis"] == "region")
    assert set(matched_region.keys()) == {
        "axis",
        "userConceptUri",
        "userConceptCode",
        "policyConceptUri",
        "policyConceptCode",
    }

    [inference_path] = result["inferencePaths"]
    assert set(inference_path.keys()) == {"axis", "fromConceptUri", "relations", "toConceptUri"}
    assert inference_path["axis"] == "region"


def test_batch_endpoint_preserves_request_order_and_policy_id_correlation():
    response = client.post(
        ENDPOINT,
        json=_payload(
            [
                {"policyId": 3, "regionScope": "NATIONAL"},
                {"policyId": 1, "regionScope": "NATIONAL"},
                {"policyId": 2, "regionScope": "NATIONAL"},
            ]
        ),
    )

    assert response.status_code == 200
    assert [r["policyId"] for r in response.json()["results"]] == [3, 1, 2]


def test_batch_endpoint_no_common_axis_returns_null_semantic_score():
    response = client.post(
        ENDPOINT,
        json=_payload([{"policyId": 1, "regionScope": "NATIONAL"}]),
    )

    assert response.status_code == 200
    [result] = response.json()["results"]
    assert result["semanticScore"] is None
    assert result["matchedConcepts"] == []
    assert result["inferencePaths"] == []


def test_batch_endpoint_missing_required_gender_returns_422():
    response = client.post(ENDPOINT, json={"user": {}, "policies": []})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_batch_endpoint_missing_policy_id_returns_422():
    response = client.post(
        ENDPOINT,
        json=_payload([{"regionScope": "NATIONAL"}]),
    )

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_batch_endpoint_invalid_gender_enum_value_returns_422():
    response = client.post(ENDPOINT, json={"user": {"gender": "UNKNOWN"}, "policies": []})

    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_batch_endpoint_invalid_age_range_returns_400():
    response = client.post(
        ENDPOINT,
        json=_payload(
            [
                {
                    "policyId": 1,
                    "regionScope": "NATIONAL",
                    "minimumAge": 40,
                    "maximumAge": 30,
                }
            ]
        ),
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_AGE_RANGE"


def test_batch_endpoint_invalid_birth_date_returns_400():
    response = client.post(
        ENDPOINT,
        json={
            "user": {"gender": "MALE", "birthDate": "2999-01-01"},
            "policies": [{"policyId": 1, "regionScope": "NATIONAL"}],
        },
    )

    assert response.status_code == 400
    assert response.json()["code"] == "INVALID_BIRTH_DATE"


def test_batch_request_schema_still_constructible_via_snake_case_kwargs():
    request = SemanticMatchBatchRequest(
        user=UserMappingInput(gender="MALE"),
        policies=[SemanticMatchBatchPolicyItem(policy_id=1, region_scope="NATIONAL")],
    )

    assert request.policies[0].policy_id == 1
