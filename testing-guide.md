# End-to-End Testing Guide

This guide walks through the complete e-commerce flow across all four microservices.

## Prerequisites

Start all services:

```bash
docker compose up -d --build
```

Wait for all services to be healthy:

```bash
docker compose ps
```

Service ports on the host:

| Service           | Host Port |
|-------------------|-----------|
| User Service      | 8010      |
| Product Service   | 8001      |
| Inventory Service | 8002      |
| Order Service     | 8003      |

---

## 1. User Registration and Authentication

### Step 1.1: Register a New User

```bash
curl -X POST "http://localhost:8010/api/v1/auth/register" \
  -H "Content-Type: application/json" \
  -d '{
    "email": "customer@example.com",
    "password": "Password123",
    "first_name": "Example",
    "last_name": "Customer",
    "phone": "555-123-4567"
  }' | jq .
```

Expected response:

```json
{
  "id": 1,
  "email": "customer@example.com",
  "first_name": "Example",
  "last_name": "Customer",
  "phone": "555-123-4567",
  "is_active": true,
  "created_at": "2026-03-23T07:43:19.959933+00:00",
  "addresses": []
}
```

### Step 1.2: Login to Get Authentication Token

```bash
curl -X POST "http://localhost:8010/api/v1/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=customer@example.com&password=Password123" | jq .
```

Expected response:

```json
{
  "access_token": "eyJhbGciOiJS...",
  "refresh_token": "eyJhbGciOiJS...",
  "token_type": "bearer"
}
```

Save the access token for subsequent requests:

```bash
TOKEN="<paste access_token value here>"
```

### Step 1.3: Verify User Authentication

```bash
curl -X GET "http://localhost:8010/api/v1/users/me" \
  -H "Authorization: Bearer $TOKEN" | jq .
```

Expected response:

```json
{
  "id": 1,
  "email": "customer@example.com",
  "first_name": "Example",
  "last_name": "Customer",
  "phone": "555-123-4567",
  "is_active": true,
  "created_at": "2026-03-23T07:43:19.959933+00:00",
  "addresses": []
}
```

---

## 2. Adding User Address

```bash
curl -X POST "http://localhost:8010/api/v1/users/me/addresses" \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "line1": "123 Example Street",
    "line2": "Apt 4B",
    "city": "Example City",
    "state": "EX",
    "postal_code": "12345",
    "country": "Example Country",
    "is_default": true
  }' | jq .
```

Expected response:

```json
{
  "id": 1,
  "line1": "123 Example Street",
  "line2": "Apt 4B",
  "city": "Example City",
  "state": "EX",
  "postal_code": "12345",
  "country": "Example Country",
  "is_default": true
}
```

---

## 3. Creating Products with Automatic Inventory

Product and inventory endpoints do not require authentication.

### Step 3.1: Create Product 1 - Smartphone

```bash
curl -X POST "http://localhost:8001/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Premium Smartphone",
    "description": "Latest model with high-end camera and long battery life",
    "category": "Electronics",
    "price": 899.99,
    "quantity": 50
  }' | jq .
```

Expected response (save the `_id` for later use):

```json
{
  "name": "Premium Smartphone",
  "description": "Latest model with high-end camera and long battery life",
  "category": "Electronics",
  "price": 899.99,
  "quantity": 50,
  "_id": "<product_id_1>",
  "created_at": "2026-03-23T07:44:05.657677",
  "updated_at": "2026-03-23T07:44:05.657682"
}
```

```bash
PRODUCT_ID_1="<paste _id value here>"
```

### Step 3.2: Create Product 2 - Wireless Headphones

```bash
curl -X POST "http://localhost:8001/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Wireless Noise-Cancelling Headphones",
    "description": "Premium headphones with active noise cancellation",
    "category": "Audio",
    "price": 249.99,
    "quantity": 100
  }' | jq .
```

```bash
PRODUCT_ID_2="<paste _id value here>"
```

### Step 3.3: Create Product 3 - Smart Watch

```bash
curl -X POST "http://localhost:8001/api/v1/products/" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "Smart Fitness Watch",
    "description": "Waterproof fitness tracker with heart rate monitoring",
    "category": "Wearables",
    "price": 179.99,
    "quantity": 75
  }' | jq .
```

```bash
PRODUCT_ID_3="<paste _id value here>"
```

---

## 4. Browsing Products and Checking Inventory

### Step 4.1: Get All Products

```bash
curl -X GET "http://localhost:8001/api/v1/products/" | jq .
```

### Step 4.2: Verify Inventory Was Created

Check inventory for Product 1:

```bash
curl -X GET "http://localhost:8002/api/v1/inventory/$PRODUCT_ID_1" | jq .
```

Expected response:

```json
{
  "id": 1,
  "product_id": "<product_id_1>",
  "available_quantity": 50,
  "reserved_quantity": 0,
  "reorder_threshold": 5
}
```

Check inventory for Product 2:

```bash
curl -X GET "http://localhost:8002/api/v1/inventory/$PRODUCT_ID_2" | jq .
```

Expected response:

```json
{
  "id": 2,
  "product_id": "<product_id_2>",
  "available_quantity": 100,
  "reserved_quantity": 0,
  "reorder_threshold": 5
}
```

### Step 4.3: Filter Products by Category

```bash
curl -X GET "http://localhost:8001/api/v1/products/?category=Electronics" | jq .
```

Returns only Electronics products.

### Step 4.4: Filter Products by Price Range

```bash
curl -X GET "http://localhost:8001/api/v1/products/?min_price=100&max_price=300" | jq .
```

Returns the Headphones and Watch (both between $100 and $300).

---

## 5. Placing Orders

Order endpoints do not require authentication. The order service validates users and products via inter-service calls.

### Step 5.1: Get User ID

Use the user ID from the registration response. In this example, `USER_ID=1`.

```bash
USER_ID="1"
```

### Step 5.2: Place an Order for a Single Product

```bash
curl -X POST "http://localhost:8003/api/v1/orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "items": [
      {
        "product_id": "'$PRODUCT_ID_1'",
        "quantity": 1,
        "price": 899.99
      }
    ],
    "shipping_address": {
      "line1": "123 Example Street",
      "line2": "Apt 4B",
      "city": "Example City",
      "state": "EX",
      "postal_code": "12345",
      "country": "Example Country"
    }
  }' | jq .
```

Expected response (save the `_id`):

```json
{
  "_id": "<order_id_1>",
  "user_id": "1",
  "items": [
    {
      "product_id": "<product_id_1>",
      "quantity": 1,
      "price": 899.99
    }
  ],
  "total_price": 899.99,
  "status": "pending",
  "shipping_address": {
    "line1": "123 Example Street",
    "line2": "Apt 4B",
    "city": "Example City",
    "state": "EX",
    "postal_code": "12345",
    "country": "Example Country"
  },
  "created_at": "2026-03-23T07:44:06.223996",
  "updated_at": "2026-03-23T07:44:06.224000"
}
```

```bash
ORDER_ID_1="<paste _id value here>"
```

### Step 5.3: Place an Order for Multiple Products

```bash
curl -X POST "http://localhost:8003/api/v1/orders/" \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "'$USER_ID'",
    "items": [
      {
        "product_id": "'$PRODUCT_ID_2'",
        "quantity": 1,
        "price": 249.99
      },
      {
        "product_id": "'$PRODUCT_ID_3'",
        "quantity": 2,
        "price": 179.99
      }
    ],
    "shipping_address": {
      "line1": "123 Example Street",
      "line2": "Apt 4B",
      "city": "Example City",
      "state": "EX",
      "postal_code": "12345",
      "country": "Example Country"
    }
  }' | jq .
```

Expected: `total_price` of 609.97 (249.99 + 2 x 179.99), status `"pending"`.

```bash
ORDER_ID_2="<paste _id value here>"
```

---

## 6. Viewing and Managing Orders

### Step 6.1: Get Order Details

```bash
curl -X GET "http://localhost:8003/api/v1/orders/$ORDER_ID_1" | jq .
```

### Step 6.2: List All Orders

```bash
curl -X GET "http://localhost:8003/api/v1/orders/" | jq .
```

Returns both orders, sorted by `created_at` descending.

### Step 6.3: Update Order Status

```bash
curl -X PUT "http://localhost:8003/api/v1/orders/$ORDER_ID_1/status" \
  -H "Content-Type: application/json" \
  -d '{"status": "paid"}' | jq .
```

Expected: Order 1 now has `"status": "paid"`.

Valid status transitions: pending -> paid -> processing -> shipped -> delivered. Orders can be cancelled from pending or paid.

### Step 6.4: Cancel an Order

```bash
curl -X DELETE "http://localhost:8003/api/v1/orders/$ORDER_ID_2"
```

Returns HTTP 204 No Content (no response body).

Verify the cancellation:

```bash
curl -X GET "http://localhost:8003/api/v1/orders/$ORDER_ID_2" | jq .
```

Expected: `"status": "cancelled"`.

### Step 6.5: Verify Inventory After Order Operations

Check Product 1 inventory (1 reserved from the order):

```bash
curl -X GET "http://localhost:8002/api/v1/inventory/$PRODUCT_ID_1" | jq .
```

Expected:

```json
{
  "id": 1,
  "product_id": "<product_id_1>",
  "available_quantity": 49,
  "reserved_quantity": 1,
  "reorder_threshold": 5
}
```

Check Product 2 inventory (released after order cancellation):

```bash
curl -X GET "http://localhost:8002/api/v1/inventory/$PRODUCT_ID_2" | jq .
```

Expected:

```json
{
  "id": 2,
  "product_id": "<product_id_2>",
  "available_quantity": 100,
  "reserved_quantity": 0,
  "reorder_threshold": 5
}
```

---

## 7. Summary

After completing all steps, you will have verified:

- User registration, login (JWT), and profile management
- Address creation for a user
- Product creation with automatic inventory record generation
- Product browsing with category and price range filters
- Inventory auto-creation and tracking
- Order placement with user/product/inventory validation
- Order status updates with valid transition enforcement
- Order cancellation with automatic inventory release
- Inventory reservation on order and release on cancellation
