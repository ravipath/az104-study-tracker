from app import app


def test_dashboard_returns_200():
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/")

    assert response.status_code == 200


def test_health_returns_200():
    app.config["TESTING"] = True
    client = app.test_client()

    response = client.get("/health")

    assert response.status_code == 200
