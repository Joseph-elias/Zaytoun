from tests.helpers import client, _clear_tables, _register_and_login, _create_land_piece, _worker_payload


def test_customer_role_can_register_and_login() -> None:
    _clear_tables()

    payload = {
        "full_name": "Customer One",
        "phone": "+2127887000",
        "role": "customer",
        "password": "secret123",
        "terms_accepted": True,
        "data_consent_accepted": True,
        "consent_version": "2026-04-13",
    }
    response = client.post("/auth/register", json=payload)
    assert response.status_code == 201

    login = client.post(
        "/auth/login",
        json={"phone": payload["phone"], "password": payload["password"], "legal_acknowledged": True},
    )
    assert login.status_code == 200
    assert login.json()["user"]["role"] == "customer"

def test_market_listing_and_order_flow() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887100")
    customer_headers = _register_and_login("customer", "+2127887200")
    worker_headers = _register_and_login("worker", "+2127887300")

    created_item = client.post(
        "/market/items",
        json={
            "item_name": "Olive Oil Premium",
            "description": "First cold press",
            "unit_label": "liter",
            "price_per_unit": 12.5,
            "quantity_available": 15,
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert created_item.status_code == 201
    item_id = created_item.json()["id"]

    customer_market = client.get("/market/items", headers=customer_headers)
    assert customer_market.status_code == 200
    assert len(customer_market.json()) == 1

    worker_market_denied = client.get("/market/items", headers=worker_headers)
    assert worker_market_denied.status_code == 403

    placed_order = client.post(
        "/market/orders",
        json={
            "market_item_id": item_id,
            "quantity_ordered": 3,
            "note": "Please deliver this week",
        },
        headers=customer_headers,
    )
    assert placed_order.status_code == 201
    assert placed_order.json()["total_price"] == "37.50"

    customer_orders = client.get("/market/orders/mine", headers=customer_headers)
    assert customer_orders.status_code == 200
    assert len(customer_orders.json()) == 1

    farmer_incoming = client.get("/market/orders/incoming", headers=farmer_headers)
    assert farmer_incoming.status_code == 200
    assert len(farmer_incoming.json()) == 1

    farmer_items = client.get("/market/items/mine", headers=farmer_headers)
    assert farmer_items.status_code == 200
    assert len(farmer_items.json()) == 1
    assert farmer_items.json()[0]["quantity_available"] == "15.00"

    too_much = client.post(
        "/market/orders",
        json={
            "market_item_id": item_id,
            "quantity_ordered": 20,
        },
        headers=customer_headers,
    )
    assert too_much.status_code == 400

def test_market_order_farmer_validation_chat_and_pickup_time() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887400")
    customer_headers = _register_and_login("customer", "+2127887500")
    other_customer_headers = _register_and_login("customer", "+2127887600")

    created_item = client.post(
        "/market/items",
        json={
            "item_name": "Validation Oil",
            "description": "chat test",
            "unit_label": "liter",
            "price_per_unit": 10,
            "quantity_available": 6,
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert created_item.status_code == 201
    item_id = created_item.json()["id"]

    placed_order = client.post(
        "/market/orders",
        json={"market_item_id": item_id, "quantity_ordered": 2},
        headers=customer_headers,
    )
    assert placed_order.status_code == 201
    order_id = placed_order.json()["id"]
    assert placed_order.json()["status"] == "pending"

    missing_pickup = client.patch(
        f"/market/orders/{order_id}/farmer-validation",
        json={"action": "validate"},
        headers=farmer_headers,
    )
    assert missing_pickup.status_code == 422

    validated = client.patch(
        f"/market/orders/{order_id}/farmer-validation",
        json={
            "action": "validate",
            "pickup_at": "2030-02-12T10:30:00",
            "note": "Ready after pressing",
        },
        headers=farmer_headers,
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "validated"
    assert validated.json()["pickup_at"].startswith("2030-02-12T10:30:00")

    customer_order_list = client.get("/market/orders/mine", headers=customer_headers)
    assert customer_order_list.status_code == 200
    assert customer_order_list.json()[0]["status"] == "validated"

    customer_message = client.post(
        f"/market/orders/{order_id}/messages",
        json={"content": "Thanks, I will come on time."},
        headers=customer_headers,
    )
    assert customer_message.status_code == 201
    assert customer_message.json()["sender_role"] == "customer"

    farmer_message = client.post(
        f"/market/orders/{order_id}/messages",
        json={"content": "Great, see you then."},
        headers=farmer_headers,
    )
    assert farmer_message.status_code == 201
    assert farmer_message.json()["sender_role"] == "farmer"

    list_messages = client.get(f"/market/orders/{order_id}/messages", headers=customer_headers)
    assert list_messages.status_code == 200
    assert len(list_messages.json()) == 2

    unauthorized_reader = client.get(f"/market/orders/{order_id}/messages", headers=other_customer_headers)
    assert unauthorized_reader.status_code == 404

def test_market_customer_can_submit_product_and_store_ratings_separately() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887700")
    customer_headers = _register_and_login("customer", "+2127887800")

    created_item = client.post(
        "/market/items",
        json={
            "item_name": "Separate Rating Oil",
            "description": "separate rating flow",
            "unit_label": "liter",
            "price_per_unit": 20,
            "quantity_available": 10,
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert created_item.status_code == 201
    item_id = created_item.json()["id"]

    placed_order = client.post(
        "/market/orders",
        json={"market_item_id": item_id, "quantity_ordered": 2},
        headers=customer_headers,
    )
    assert placed_order.status_code == 201
    order_id = placed_order.json()["id"]

    validated = client.patch(
        f"/market/orders/{order_id}/farmer-validation",
        json={"action": "validate", "pickup_at": "2030-03-20T12:00:00", "note": "ready"},
        headers=farmer_headers,
    )
    assert validated.status_code == 200

    product_only = client.patch(
        f"/market/orders/{order_id}/customer-review",
        json={"product_rating": 5, "product_review": "great quality"},
        headers=customer_headers,
    )
    assert product_only.status_code == 200
    assert product_only.json()["product_rating"] == 5
    assert product_only.json()["product_review"] == "great quality"
    assert product_only.json()["market_rating"] is None

    store_only = client.patch(
        f"/market/orders/{order_id}/customer-review",
        json={"market_rating": 4, "market_review": "smooth pickup"},
        headers=customer_headers,
    )
    assert store_only.status_code == 200
    assert store_only.json()["product_rating"] == 5
    assert store_only.json()["market_rating"] == 4
    assert store_only.json()["market_review"] == "smooth pickup"

def test_market_product_rating_is_aggregated_per_item_independently() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887900")
    customer_headers = _register_and_login("customer", "+2127887910")

    item_a = client.post(
        "/market/items",
        json={
            "item_name": "Item A",
            "description": "A",
            "unit_label": "kg",
            "price_per_unit": 8,
            "quantity_available": 20,
            "is_active": True,
        },
        headers=farmer_headers,
    )
    item_b = client.post(
        "/market/items",
        json={
            "item_name": "Item B",
            "description": "B",
            "unit_label": "kg",
            "price_per_unit": 9,
            "quantity_available": 20,
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert item_a.status_code == 201
    assert item_b.status_code == 201

    order_a = client.post(
        "/market/orders",
        json={"market_item_id": item_a.json()["id"], "quantity_ordered": 1},
        headers=customer_headers,
    )
    order_b = client.post(
        "/market/orders",
        json={"market_item_id": item_b.json()["id"], "quantity_ordered": 1},
        headers=customer_headers,
    )
    assert order_a.status_code == 201
    assert order_b.status_code == 201

    for oid in [order_a.json()["id"], order_b.json()["id"]]:
        validated = client.patch(
            f"/market/orders/{oid}/farmer-validation",
            json={"action": "validate", "pickup_at": "2030-03-21T10:00:00"},
            headers=farmer_headers,
        )
        assert validated.status_code == 200

    rate_a = client.patch(
        f"/market/orders/{order_a.json()['id']}/customer-review",
        json={"product_rating": 5, "market_rating": 4},
        headers=customer_headers,
    )
    rate_b = client.patch(
        f"/market/orders/{order_b.json()['id']}/customer-review",
        json={"product_rating": 2},
        headers=customer_headers,
    )
    assert rate_a.status_code == 200
    assert rate_b.status_code == 200

    items = client.get("/market/items", headers=customer_headers)
    assert items.status_code == 200
    data = {row["item_name"]: row for row in items.json()}

    assert data["Item A"]["product_rating_count"] == 1
    assert data["Item A"]["product_rating_avg"] == 5.0

    assert data["Item B"]["product_rating_count"] == 1
    assert data["Item B"]["product_rating_avg"] == 2.0

    # Store rating is aggregated at farmer level and should reflect only the
    # order where store rating was submitted.
    assert data["Item A"]["farmer_rating_count"] == 1
    assert data["Item B"]["farmer_rating_count"] == 1
    assert data["Item A"]["farmer_rating_avg"] == 4.0
    assert data["Item B"]["farmer_rating_avg"] == 4.0



def test_market_inventory_link_reserve_pickup_and_pending_flow() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887920")
    customer_headers = _register_and_login("customer", "+2127887930")

    inv = client.post(
        "/olive-inventory-items",
        json={
            "inventory_year": 2026,
            "item_name": "Inventory EVOO",
            "unit_label": "liter",
            "quantity_on_hand": 30,
            "default_price_per_unit": 16,
            "notes": "market-linked",
        },
        headers=farmer_headers,
    )
    assert inv.status_code == 201
    inv_id = inv.json()["id"]

    item = client.post(
        "/market/items",
        json={
            "item_name": "Linked Oil",
            "unit_label": "kg",
            "price_per_unit": 16,
            "quantity_available": 50,
            "linked_inventory_item_id": inv_id,
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert item.status_code == 201
    assert item.json()["unit_label"] == "liter"
    assert item.json()["linked_inventory_item_id"] == inv_id

    placed = client.post(
        "/market/orders",
        json={"market_item_id": item.json()["id"], "quantity_ordered": 8},
        headers=customer_headers,
    )
    assert placed.status_code == 201
    order_id = placed.json()["id"]

    inv_before_validate = client.get("/olive-inventory-items/mine?inventory_year=2026", headers=farmer_headers)
    assert inv_before_validate.status_code == 200
    assert inv_before_validate.json()[0]["quantity_on_hand"] == "30.00"
    assert inv_before_validate.json()[0]["quantity_pending"] == "0.00"

    validated = client.patch(
        f"/market/orders/{order_id}/farmer-validation",
        json={"action": "validate", "pickup_at": "2030-04-01T12:00:00"},
        headers=farmer_headers,
    )
    assert validated.status_code == 200
    assert validated.json()["status"] == "validated"
    assert validated.json()["inventory_reserved_quantity"] == "8.00"

    customer_orders = client.get("/market/orders/mine", headers=customer_headers)
    assert customer_orders.status_code == 200
    pickup_code = customer_orders.json()[0]["pickup_code"]
    assert isinstance(pickup_code, str)
    assert len(pickup_code) >= 4

    inv_after_validate = client.get("/olive-inventory-items/mine?inventory_year=2026", headers=farmer_headers)
    assert inv_after_validate.status_code == 200
    assert inv_after_validate.json()[0]["quantity_on_hand"] == "22.00"
    assert inv_after_validate.json()[0]["quantity_pending"] == "8.00"

    wrong_pickup = client.patch(
        f"/market/orders/{order_id}/pickup-confirmation",
        json={"pickup_code": "000000"},
        headers=farmer_headers,
    )
    assert wrong_pickup.status_code == 400

    pickup_ok = client.patch(
        f"/market/orders/{order_id}/pickup-confirmation",
        json={"pickup_code": pickup_code},
        headers=farmer_headers,
    )
    assert pickup_ok.status_code == 200
    assert pickup_ok.json()["status"] == "picked_up"

    inv_after_pickup = client.get("/olive-inventory-items/mine?inventory_year=2026", headers=farmer_headers)
    assert inv_after_pickup.status_code == 200
    assert inv_after_pickup.json()[0]["quantity_on_hand"] == "22.00"
    assert inv_after_pickup.json()[0]["quantity_pending"] == "0.00"


def test_market_inventory_shortage_alert_does_not_block_validation() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887940")
    customer_headers = _register_and_login("customer", "+2127887950")

    inv = client.post(
        "/olive-inventory-items",
        json={
            "inventory_year": 2026,
            "item_name": "Low Stock Oil",
            "unit_label": "liter",
            "quantity_on_hand": 3,
            "default_price_per_unit": 10,
            "notes": None,
        },
        headers=farmer_headers,
    )
    assert inv.status_code == 201

    item = client.post(
        "/market/items",
        json={
            "item_name": "Shortage Item",
            "unit_label": "liter",
            "price_per_unit": 10,
            "quantity_available": 20,
            "linked_inventory_item_id": inv.json()["id"],
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert item.status_code == 201

    order = client.post(
        "/market/orders",
        json={"market_item_id": item.json()["id"], "quantity_ordered": 9},
        headers=customer_headers,
    )
    assert order.status_code == 201

    validated = client.patch(
        f"/market/orders/{order.json()['id']}/farmer-validation",
        json={"action": "validate", "pickup_at": "2030-04-02T10:00:00"},
        headers=farmer_headers,
    )
    assert validated.status_code == 200
    assert validated.json()["inventory_shortage_alert"] is True
    assert validated.json()["inventory_reserved_quantity"] == "3.00"


def test_market_cancel_restores_reserved_inventory() -> None:
    _clear_tables()

    farmer_headers = _register_and_login("farmer", "+2127887960")
    customer_headers = _register_and_login("customer", "+2127887970")

    inv = client.post(
        "/olive-inventory-items",
        json={
            "inventory_year": 2026,
            "item_name": "Cancelable Stock",
            "unit_label": "liter",
            "quantity_on_hand": 12,
            "default_price_per_unit": 9,
            "notes": None,
        },
        headers=farmer_headers,
    )
    assert inv.status_code == 201

    item = client.post(
        "/market/items",
        json={
            "item_name": "Cancelable Listing",
            "unit_label": "liter",
            "price_per_unit": 9,
            "quantity_available": 12,
            "linked_inventory_item_id": inv.json()["id"],
            "is_active": True,
        },
        headers=farmer_headers,
    )
    assert item.status_code == 201

    order = client.post(
        "/market/orders",
        json={"market_item_id": item.json()["id"], "quantity_ordered": 5},
        headers=customer_headers,
    )
    assert order.status_code == 201

    validated = client.patch(
        f"/market/orders/{order.json()['id']}/farmer-validation",
        json={"action": "validate", "pickup_at": "2030-04-03T14:00:00"},
        headers=farmer_headers,
    )
    assert validated.status_code == 200

    canceled = client.patch(
        f"/market/orders/{order.json()['id']}/farmer-validation",
        json={"action": "cancel", "note": "Customer asked to cancel"},
        headers=farmer_headers,
    )
    assert canceled.status_code == 200
    assert canceled.json()["status"] == "canceled"

    inventory_rows = client.get("/olive-inventory-items/mine?inventory_year=2026", headers=farmer_headers)
    assert inventory_rows.status_code == 200
    assert inventory_rows.json()[0]["quantity_on_hand"] == "12.00"
    assert inventory_rows.json()[0]["quantity_pending"] == "0.00"
