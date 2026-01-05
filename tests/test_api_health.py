def test_health_check(client):
    """
    Test the health check endpoint.
    It should return 200 or 503 (depending on service availability)
    but always return a valid JSON structure.
    """
    response = client.get("/health")
    assert response.status_code in [200, 503]
    
    data = response.json()
    assert "status" in data
    assert "version" in data
    assert "services" in data
