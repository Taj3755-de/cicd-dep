from app.app import app

def test_home_route():
    client = app.test_client()
    response = client.get('/')
    assert response.status_code == 200
    json_data = response.get_json()
    assert json_data["message"] == "Hello from Flask App on Kubernetes!"
