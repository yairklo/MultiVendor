import urllib.request
import json
import sys

def req(url, method="GET", data=None, token=None):
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    
    if data:
        data = json.dumps(data).encode("utf-8")
        
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request) as response:
            return response.status, json.loads(response.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

# Login
status, res = req("http://localhost:8000/api/v1/auth/login", method="POST", data={"email": "customer_test@example.com", "password": "password123"})
if status != 200:
    print("Login failed:", res)
    sys.exit(1)

token = res["access_token"]

# Get cart
status, res = req("http://localhost:8000/api/v1/store/test-tenant/cart", method="GET", token=token)
if status != 200:
    print("Cart fetch failed:", res)
    sys.exit(1)

cart_id = res.get("cart_id")

# Checkout
checkout_data = {
    "cart_id": cart_id,
    "payment_token": "987e6543-e21b-34d3-b456-426614174999",
    "shipping_address": {
        "full_name": "Test User",
        "email": "test@example.com",
        "address_line_1": "123 Main St"
    },
    "shipping_method_id": 1
}

status, res = req("http://localhost:8000/api/v1/store/test-tenant/cart/checkout", method="POST", data=checkout_data, token=token)
print("Checkout status:", status)
print("Checkout response:", res)
