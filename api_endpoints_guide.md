# LedgerMind API Endpoints Guide

This document contains a list of all endpoints across the LedgerMind microservices architecture. You can access these endpoints either **directly** via the specific microservice URL or **through the API Gateway**.

## 🚀 API Gateway (Recommended for Production)
**Gateway Base URL:** `https://ledgermind-api-gateway.onrender.com`

Using the Gateway is recommended because it handles unified authentication and simplifies CORS when connecting from your frontend.
Example: `https://ledgermind-api-gateway.onrender.com/api/v1/users/login/`

---

## 1. User & Business Service
**Direct URL:** `https://ledgermind-user-service.onrender.com`

### Authentication & Users
* **Register:** `POST /api/v1/users/register/` (Direct or via Gateway `/api/v1/users/...`)
* **Login:** `POST /api/v1/users/login/`
* **Refresh Token:** `POST /api/v1/users/token/refresh/`
* **Profile:** `GET/PUT/PATCH /api/v1/users/profile/` (Auth required)

### Businesses
* **List/Create:** `GET/POST /api/v1/businesses/` (Direct or via Gateway `/api/v1/businesses/...`)
* **Detail/Update/Delete:** `GET/PUT/PATCH/DELETE /api/v1/businesses/<uuid>/`

---

## 2. Transaction Service
**Direct URL:** `https://ledgermind-transaction-service.onrender.com`

### Categories
* **List/Create:** `GET/POST /api/v1/categories/` (Direct or via Gateway `/api/v1/categories/...`)

### Transactions
* **List/Create:** `GET/POST /api/v1/transactions/` (Direct or via Gateway `/api/v1/transactions/...`)
* **Detail/Update/Delete:** `GET/PUT/PATCH/DELETE /api/v1/transactions/<uuid>/`
* **Bulk Upload (CSV):** `POST /api/v1/transactions/upload-csv/`

---

## 3. AI Categorization Service
**Direct URL:** `https://ledgermind-ai-service.onrender.com`

### AI Operations
* **Categorize Single:** `POST /api/v1/categorize/` (Direct or via Gateway `/api/v1/categorize/...`)
* **Bulk Categorize:** `POST /api/v1/categorize/bulk/` (Direct or via Gateway `/api/v1/categorize/bulk/`)

---

## 4. Analytics Service
**Direct URL:** `https://ledgermind-analytics-service.onrender.com`

### Insights
* **Dashboard Data:** `GET /api/v1/analytics/dashboard/<business_uuid>/` (Direct or via Gateway `/api/v1/analytics/dashboard/...`)
* **Cashflow Forecast:** `GET /api/v1/analytics/forecasting/cashflow/<business_uuid>/`
* **AI Credit Score:** `GET /api/v1/analytics/credit-score/<business_uuid>/`

---

## 5. Payment Service
**Direct URL:** `https://ledgermind-payment-service.onrender.com`

### Interswitch Payments
* **List Payments:** `GET /api/v1/payments/` (Direct or via Gateway `/api/v1/payments/...`)
* **Initiate Payment:** `POST /api/v1/payments/initiate/`
* **Authenticate OTP:** `POST /api/v1/payments/authenticate-otp/`
* **Verify Status:** `POST /api/v1/payments/verify/`

---

## 💡 Important Notes
1. **Unified Token:** Since I fixed the `SECRET_KEY` sharing, the token you get from the **User Service** login will now work for **ALL** direct service URLs and the **Gateway URL**.
2. **Trailing Slashes:** Django requires a trailing slash (`/`) at the end of every URL.
3. **Internal Key:** Some endpoints are restricted to "Service-to-Service" calls. For your frontend/mobile app, always use the Bearer JWT token from login.
