# LedgerMind API Gateway Guide

This guide provides the complete list of endpoints for LedgerMind. To ensure proper session handling, CORS management, and security, **always use the API Gateway URL** as your base when interacting with the system from your frontend or mobile app.

**Gateway Base URL:** `https://ledgermind-api-gateway.onrender.com`

---

## 1. Authentication & Users (User Service)
* **Register User:** `POST /api/v1/users/register/`
  * Body: `{"email": "...", "password": "...", "first_name": "...", "last_name": "..."}`
* **Login:** `POST /api/v1/users/login/`
  * Body: `{"email": "...", "password": "..."}`
  * Response: `{ "access": "...", "refresh": "..." }`
* **Refresh Token:** `POST /api/v1/users/token/refresh/`
  * Body: `{"refresh": "..."}`
* **Get/Update Profile:** `GET`, `PUT`, `PATCH /api/v1/users/profile/`
  * Headers: `Authorization: Bearer <access_token>`

## 2. Business Management (User Service)
* **List / Create Business:** `GET`, `POST /api/v1/businesses/`
* **Detail / Update / Delete:** `GET`, `PUT`, `PATCH`, `DELETE /api/v1/businesses/<uuid>/`
  * Headers: `Authorization: Bearer <access_token>`

## 3. Categories (Transaction Service)
* **List / Create Categories:** `GET`, `POST /api/v1/categories/`
  * Headers: `Authorization: Bearer <access_token>`

## 4. Transactions (Transaction Service)
* **List / Create Transactions:** `GET`, `POST /api/v1/transactions/`
  * Body: `{"business": "<uuid>", "amount": "10.00", "type": "EXPENSE", "description": "...", "date": "YYYY-MM-DD"}`
* **Detail / Update / Delete:** `GET`, `PUT`, `PATCH`, `DELETE /api/v1/transactions/<uuid>/`
* **Bulk Upload (CSV):** `POST /api/v1/transactions/upload-csv/`
  * Body: `multipart/form-data` with `business_id` and `file`.
  * Headers: `Authorization: Bearer <access_token>`

## 5. AI Categorization (AI Service)
* **Categorize Single:** `POST /api/v1/categorize/`
  * Body: `{"description": "Uber trip", "amount": "-25.00"}`
* **Bulk Categorize:** `POST /api/v1/categorize/bulk/`
  * Body: `{"transactions": [{"description": "..."}, ...]}`
  * Headers: `Authorization: Bearer <access_token>`

## 6. Analytics & Insights (Analytics Service)
* **Dashboard Stats:** `GET /api/v1/analytics/dashboard/<business_uuid>/`
* **Cashflow Forecast:** `GET /api/v1/analytics/forecasting/cashflow/<business_uuid>/`
* **AI Credit Score:** `GET /api/v1/analytics/credit-score/<business_uuid>/`
  * Headers: `Authorization: Bearer <access_token>`

## 7. Payments & Interswitch (Payment Service)
* **List Payments:** `GET /api/v1/payments/`
* **Initiate Payment:** `POST /api/v1/payments/initiate/`
  * Body: `{"amount": "5000", "currency": "NGN", "authData": "...", "pan": "..."}`
* **Authenticate OTP:** `POST /api/v1/payments/authenticate-otp/`
  * Body: `{"transaction_ref": "...", "otp": "...", "paymentId": "..."}`
* **Verify Transaction:** `POST /api/v1/payments/verify/`
  * Body: `{"transaction_ref": "..."}`
  * Headers: `Authorization: Bearer <access_token>`

---

## Important Implementation Notes
1. **Trailing Slashes:** Django is strict about trailing slashes. Use `/api/v1/users/login/` (with slash) instead of `/api/v1/users/login`.
2. **Authorization Header:** For all endpoints except Register and Login, you must include the header:
   `Authorization: Bearer <your_access_token>`
3. **Gateway Strategy:** The Gateway automatically routes your request based on the first word after `/api/v1/`. For example, any request starting with `/api/v1/categorize/` is routed to the AI service.
