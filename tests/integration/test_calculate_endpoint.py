"""Integration test for the stateless /calculate endpoint.

This endpoint runs the calculation engine without requiring a database,
so it can be tested without PostgreSQL.
"""

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client():
    return TestClient(app)


BASE_PAYLOAD = {
    "job_name": "Integration Test Box",
    "quantity": 1000,
    "complexity_tier": 3,
    "rush_order": False,
    "dimensions": {
        "flat_width": 300,
        "flat_height": 400,
        "spine_depth": 25,
    },
    "materials": {
        "board_type": "dutch_grey_2mm",
        "board_thickness": 2.0,
        "outer_wrap": "buckram_cloth",
        "liner": "uncoated_paper_120gsm",
    },
    "operations": ["cutting", "wrapping", "assembly"],
}


class TestCalculateEndpoint:
    """Test the stateless /api/v1/estimates/calculate endpoint."""

    def test_returns_200(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        assert resp.status_code == 200

    def test_response_structure(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        data = resp.json()
        assert "breakdown" in data
        assert "confidence_interval" in data
        assert "confidence_level" in data

        bd = data["breakdown"]
        assert "total_cost" in bd
        assert "unit_cost" in bd
        assert "material_costs" in bd
        assert "labor_hours" in bd
        assert "labor_cost" in bd
        assert "overhead_cost" in bd
        assert "wastage_cost" in bd
        assert "complexity_adjustment" in bd
        assert "rush_premium" in bd
        assert "audit_trail" in bd

    def test_total_cost_positive(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        bd = resp.json()["breakdown"]
        assert float(bd["total_cost"]) > 0

    def test_unit_cost_is_total_divided_by_quantity(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        bd = resp.json()["breakdown"]
        total = float(bd["total_cost"])
        unit = float(bd["unit_cost"])
        assert abs(unit - total / 1000) < 0.01

    def test_confidence_interval_bounds(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        data = resp.json()
        low, high = float(data["confidence_interval"][0]), float(data["confidence_interval"][1])
        total = float(data["breakdown"]["total_cost"])
        assert low < total < high

    def test_rush_order_increases_cost(self, client):
        normal = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD).json()
        rush_payload = {**BASE_PAYLOAD, "rush_order": True}
        rush = client.post("/api/v1/estimates/calculate", json=rush_payload).json()

        normal_total = float(normal["breakdown"]["total_cost"])
        rush_total = float(rush["breakdown"]["total_cost"])
        rush_premium = float(rush["breakdown"]["rush_premium"])

        assert rush_total > normal_total
        assert rush_premium > 0

    def test_higher_quantity_higher_total(self, client):
        low_q = {**BASE_PAYLOAD, "quantity": 100}
        high_q = {**BASE_PAYLOAD, "quantity": 5000}

        low_resp = client.post("/api/v1/estimates/calculate", json=low_q).json()
        high_resp = client.post("/api/v1/estimates/calculate", json=high_q).json()

        assert float(high_resp["breakdown"]["total_cost"]) > float(low_resp["breakdown"]["total_cost"])

    def test_higher_complexity_higher_cost(self, client):
        tier1 = {**BASE_PAYLOAD, "complexity_tier": 1}
        tier5 = {**BASE_PAYLOAD, "complexity_tier": 5}

        t1 = client.post("/api/v1/estimates/calculate", json=tier1).json()
        t5 = client.post("/api/v1/estimates/calculate", json=tier5).json()

        assert float(t5["breakdown"]["total_cost"]) > float(t1["breakdown"]["total_cost"])
        assert float(t5["breakdown"]["complexity_adjustment"]) > float(t1["breakdown"]["complexity_adjustment"])

    def test_material_costs_present(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        materials = resp.json()["breakdown"]["material_costs"]
        assert "board" in materials
        assert float(materials["board"]) > 0

    def test_labor_hours_per_operation(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        hours = resp.json()["breakdown"]["labor_hours"]
        for op in ["cutting", "wrapping", "assembly"]:
            assert op in hours
            assert hours[op] > 0

    def test_audit_trail_present(self, client):
        resp = client.post("/api/v1/estimates/calculate", json=BASE_PAYLOAD)
        trail = resp.json()["breakdown"]["audit_trail"]
        assert len(trail) > 0
        assert trail[0]["step"] == "context_build"


class TestCalculateValidation:
    """Test input validation on the calculate endpoint."""

    def test_missing_job_name(self, client):
        payload = {**BASE_PAYLOAD}
        del payload["job_name"]
        resp = client.post("/api/v1/estimates/calculate", json=payload)
        assert resp.status_code == 422

    def test_quantity_too_high(self, client):
        payload = {**BASE_PAYLOAD, "quantity": 200000}
        resp = client.post("/api/v1/estimates/calculate", json=payload)
        assert resp.status_code == 422

    def test_zero_quantity(self, client):
        payload = {**BASE_PAYLOAD, "quantity": 0}
        resp = client.post("/api/v1/estimates/calculate", json=payload)
        assert resp.status_code == 422

    def test_no_operations(self, client):
        payload = {**BASE_PAYLOAD, "operations": []}
        resp = client.post("/api/v1/estimates/calculate", json=payload)
        assert resp.status_code == 422

    def test_invalid_complexity_tier(self, client):
        payload = {**BASE_PAYLOAD, "complexity_tier": 10}
        resp = client.post("/api/v1/estimates/calculate", json=payload)
        assert resp.status_code == 422

    def test_dimension_too_small(self, client):
        payload = {**BASE_PAYLOAD, "dimensions": {"flat_width": 1, "flat_height": 400}}
        resp = client.post("/api/v1/estimates/calculate", json=payload)
        assert resp.status_code == 422
