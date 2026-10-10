from app import app, parse_ipv4_cidr


def client():
    app.config["TESTING"] = True
    return app.test_client()


def test_empty_calculator_returns_200():
    response = client().get("/")

    assert response.status_code == 200
    assert "Plan a VNet" in response.get_data(as_text=True)


def test_example_normalizes_and_teaches_the_calculation():
    response = client().post("/", data={"vnet_cidr": "10.0.5.23/20"})
    page = response.get_data(as_text=True)

    assert response.status_code == 200
    assert "10.0.0.0/20" in page
    assert "255.255.240.0" in page
    assert "0–15" in page
    assert "10.0.15.255" in page
    assert "4,096 − 5 = 4,091" in page


def test_subnet_must_be_contained_and_at_least_a_slash_29():
    response = client().post(
        "/",
        data={
            "vnet_cidr": "10.0.0.0/24",
            "subnet_name": ["outside", "too-small"],
            "subnet_cidr": ["10.0.1.0/29", "10.0.0.0/30"],
        },
    )
    page = response.get_data(as_text=True)

    assert "outside the parent VNet" in page
    assert "must be /29 or larger" in page


def test_overlapping_subnet_is_rejected_while_first_is_accepted():
    response = client().post(
        "/",
        data={
            "vnet_cidr": "10.0.0.0/16",
            "subnet_name": ["web", "api"],
            "subnet_cidr": ["10.0.1.0/24", "10.0.1.128/25"],
        },
    )
    page = response.get_data(as_text=True)

    assert "web" in page
    assert "overlaps accepted subnet" in page
    assert "api" in page


def test_parser_returns_the_entered_ip_and_canonical_network():
    entered, network = parse_ipv4_cidr("10.0.5.23/20")

    assert str(entered) == "10.0.5.23"
    assert str(network) == "10.0.0.0/20"


def test_health_returns_200():
    response = client().get("/health")

    assert response.status_code == 200
    assert response.json == {"app": "azure-subnet-calculator", "status": "healthy"}
