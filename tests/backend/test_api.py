from __future__ import annotations

import pytest


VALID_INTERPRETATIONS = {
    "Guclu Bayes kaniti",
    "Orta Bayes kaniti",
    "Zayif Bayes kaniti",
}


class TestHealthEndpoint:
    def test_health_endpoint(self, client) -> None:
        response = client.get("/health")
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "ok"
        assert payload["service"] == "backend"


class TestCoreAnalysis:
    def test_real_dataset_success(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["analysis_summary"]["total_orders"] == 5343
        assert payload["analysis_summary"]["unique_items"] == 32
        assert payload["analysis_summary"]["rules_found"] > 0
        assert payload["analysis_summary"]["packages_generated"] > 0

    def test_response_has_all_fields(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        assert response.status_code == 200
        assert {"analysis_summary", "bayes_rules", "menu_packages", "monthly_trend"} <= set(payload)


class TestBayesValues:
    def test_bayes_probabilities_between_0_and_1(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        for rule in payload["bayes_rules"]:
            assert 0 <= rule["prior_probability"] <= 1
            assert 0 <= rule["posterior_probability"] <= 1

    def test_posterior_greater_than_prior(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        for rule in payload["bayes_rules"]:
            assert rule["posterior_probability"] > rule["prior_probability"]

    def test_bayes_factor_positive(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        for rule in payload["bayes_rules"]:
            assert rule["bayes_factor"] > 0

    def test_interpretation_values_are_valid(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        for rule in payload["bayes_rules"]:
            assert rule["interpretation"] in VALID_INTERPRETATIONS


class TestFilters:
    def test_category_filter_asian(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv", params={"category_filter": "Asian"})
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["analysis_summary"]["active_category_filter"] == "Asian"
        assert payload["analysis_summary"]["total_orders"] < 5343

    def test_category_filter_italian(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv", params={"category_filter": "Italian"})
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["analysis_summary"]["active_category_filter"] == "Italian"

    def test_time_filter_dinner(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv", params={"time_filter": "dinner"})
        payload = response.json()

        assert response.status_code == 200
        assert payload["status"] == "success"
        assert payload["analysis_summary"]["active_time_filter"] == "dinner"
        assert payload["analysis_summary"]["time_filter_order_count"] < 5343


class TestErrorHandling:
    def test_empty_file_returns_error(self, post_csv) -> None:
        response = post_csv(b"", filename="empty.csv")
        payload = response.json()

        assert response.status_code == 400
        assert payload["status"] == "error"

    def test_invalid_category_filter(self, post_csv, real_csv) -> None:
        response = post_csv(
            real_csv,
            filename="real_dataset.csv",
            params={"category_filter": "Japanese"},
        )
        payload = response.json()

        assert response.status_code == 400
        assert payload["status"] == "error"


class TestPricing:
    def test_price_opportunity_equals_price_times_factor(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        for package in payload["menu_packages"]:
            expected_score = package["package_total_price"] * package["bayes_factor"]
            assert package["price_opportunity_score"] == pytest.approx(expected_score, abs=0.01)


class TestMonthlyTrend:
    def test_monthly_trend_has_three_months(self, post_csv, real_csv) -> None:
        response = post_csv(real_csv, filename="real_dataset.csv")
        payload = response.json()

        assert {"1", "2", "3"} <= set(payload["monthly_trend"]["months"])
