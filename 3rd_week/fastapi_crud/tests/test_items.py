def test_create_item(client):
    response = client.post(
        "/items/",
        json={"name": "Widget", "price": 19.99, "is_available": True},
    )
    assert response.status_code == 201
    data = response.json()
    assert data["name"] == "Widget"
    assert data["price"] == 19.99
    assert data["is_available"] is True
    assert "id" in data


def test_create_item_default_is_available(client):
    response = client.post("/items/", json={"name": "Gadget", "price": 5.5})
    assert response.status_code == 201
    assert response.json()["is_available"] is True


def test_create_item_invalid_price(client):
    response = client.post("/items/", json={"name": "Bad", "price": 0})
    assert response.status_code == 422


def test_create_item_negative_price(client):
    response = client.post("/items/", json={"name": "Bad", "price": -10})
    assert response.status_code == 422


def test_create_item_empty_name(client):
    response = client.post("/items/", json={"name": "", "price": 10})
    assert response.status_code == 422


def test_create_item_missing_fields(client):
    response = client.post("/items/", json={})
    assert response.status_code == 422


def test_read_items_empty(client):
    response = client.get("/items/")
    assert response.status_code == 200
    assert response.json() == []


def test_read_items(client, sample_product):
    response = client.get("/items/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["id"] == sample_product["id"]


def test_read_items_pagination(client):
    for i in range(5):
        client.post("/items/", json={"name": f"P{i}", "price": 10 + i})

    response = client.get("/items/", params={"skip": 2, "limit": 2})
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2
    assert data[0]["name"] == "P2"
    assert data[1]["name"] == "P3"


def test_read_item(client, sample_product):
    response = client.get(f"/items/{sample_product['id']}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == sample_product["id"]
    assert data["name"] == sample_product["name"]


def test_read_item_not_found(client):
    response = client.get("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_update_item(client, sample_product):
    response = client.put(
        f"/items/{sample_product['id']}",
        json={"name": "Updated", "price": 49.99, "is_available": False},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Updated"
    assert data["price"] == 49.99
    assert data["is_available"] is False


def test_update_item_not_found(client):
    response = client.put(
        "/items/999",
        json={"name": "Updated", "price": 49.99, "is_available": False},
    )
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"


def test_update_item_invalid_data(client, sample_product):
    response = client.put(
        f"/items/{sample_product['id']}",
        json={"name": "", "price": -5},
    )
    assert response.status_code == 422


def test_delete_item(client, sample_product):
    response = client.delete(f"/items/{sample_product['id']}")
    assert response.status_code == 200
    assert response.json() == {
        "message": f"Product {sample_product['id']} deleted successfully"
    }

    response = client.get(f"/items/{sample_product['id']}")
    assert response.status_code == 404


def test_delete_item_not_found(client):
    response = client.delete("/items/999")
    assert response.status_code == 404
    assert response.json()["detail"] == "Product not found"
