# API test data

This guide targets the Flask API in `app.py`, which the frontend calls at
`http://127.0.0.1:5000`. Start it from the project root with:

```powershell
.\.venv\Scripts\python.exe app.py
```

The examples use PowerShell. Run them in order. Replace `$token` with the
token from the admin login if you are already logged in.

## Common setup

```powershell
$base = "http://127.0.0.1:5000"
$json = @{ "Content-Type" = "application/json" }
$token = "PASTE_ADMIN_TOKEN_HERE"
$auth = @{ "Content-Type" = "application/json"; Authorization = "Bearer $token" }
```

## Health and root endpoints

```powershell
Invoke-RestMethod "$base/health"
Invoke-RestMethod "$base/"
```

Expected health response:

```json
{"status":"healthy","model":"catboost_fraud_model.joblib"}
```

## Authentication endpoints

### Login

For the standalone port-8001 service, use the bootstrap admin configured in
`.env`. In your current database the admin email is `admin@example.com`; use
the value of `AUTH_BOOTSTRAP_PASSWORD` from `.env` as the password. The
`admin@transferguard.demo` / `transfer-demo-2026` credentials belong to the
separate port-5000 demo user store and will not work on port 8001.

```powershell
$login = Invoke-RestMethod "$base/api/v1/auth/login" -Method Post -Headers $json -Body (@{
  email = "admin@example.com"
  password = "PASTE_AUTH_BOOTSTRAP_PASSWORD_HERE"
} | ConvertTo-Json)
$token = $login.token
$auth = @{ "Content-Type" = "application/json"; Authorization = "Bearer $token" }
$login
```

For Swagger UI, enter this valid JSON body. Do not use PowerShell syntax
(`=`) in the Swagger request body:

```json
{
  "email": "admin@example.com",
  "password": "YOUR_AUTH_BOOTSTRAP_PASSWORD"
}
```

Open Swagger from `http://127.0.0.1:8001/docs` or
`http://localhost:8001/docs`, not from a local `file://` page.

### Request a password-reset token

In development, the response includes `reset_token`. Do not expose that token
in production logs or client responses.

```powershell
$resetRequest = Invoke-RestMethod "$base/api/v1/auth/forgot-password" -Method Post -Headers $json -Body (@{
  email = "qa.analyst@transferguard.demo"
} | ConvertTo-Json)
$resetRequest
```

### Reset a password

Use the `reset_token` returned above. The password must be at least 12
characters for the database helper.

```powershell
Invoke-RestMethod "$base/api/v1/auth/reset-password" -Method Post -Headers $json -Body (@{
  token = $resetRequest.reset_token
  password = "Qa-Analyst-New-2026!"
} | ConvertTo-Json)
```

### Logout

Run this last because it revokes the current admin token.

```powershell
Invoke-RestMethod "$base/api/v1/auth/logout" -Method Post -Headers $auth
```

## Admin user-management endpoints

All user-management requests require `Authorization: Bearer <admin-token>`.

### List users

```powershell
$users = Invoke-RestMethod "$base/api/v1/users" -Headers $auth
$users
```

### Create a test analyst

Use a unique email if the request has already been run.

The standalone API returns `409 Conflict` when the email already exists. Use
another email, or update the existing user instead of submitting the same
create request again.

Deleting an ID that is already deleted or not present returns `404 Not Found`.
Refresh the user list and use the current ID shown by the API.

```powershell
$created = Invoke-RestMethod "$base/api/v1/users" -Method Post -Headers $auth -Body (@{
  name = "QA Fraud Analyst"
  email = "qa.analyst@transferguard.demo"
  password = "Qa-Analyst-2026!"
  role = "analyst"
} | ConvertTo-Json)
$testUserId = $created.id
$created
```

### Update the test analyst

```powershell
Invoke-RestMethod "$base/api/v1/users/$testUserId" -Method Patch -Headers $auth -Body (@{
  name = "QA Senior Fraud Analyst"
  role = "compliance"
  active = $true
} | ConvertTo-Json)
```

### Reset the test analyst password as admin

```powershell
Invoke-RestMethod "$base/api/v1/users/$testUserId/reset-password" -Method Post -Headers $auth -Body (@{
  password = "Qa-Analyst-Reset-2026!"
} | ConvertTo-Json)
```

### Delete the test analyst

Run this after the other user-management checks so the test data is cleaned
up. Never use the admin’s own ID here.

```powershell
Invoke-RestMethod "$base/api/v1/users/$testUserId" -Method Delete -Headers $auth
```

## Fraud transaction endpoints

These endpoints currently do not require an auth header.

### List transaction history

```powershell
Invoke-RestMethod "$base/api/v1/transactions"
```

### Rule-engine sample: blacklisted device

This payload should be rejected by Stage 1 and is the quickest prediction
smoke test. `Time`, `Amount`, and all `V1`–`V28` fields are included so the
same payload can also be used for the ML path after removing the rule flag.

```powershell
$fraudSample = @{
  Time = 86400
  Amount = 1250.75
  is_blacklisted_device = 1
  V1 = 0.12; V2 = -0.34; V3 = 0.56; V4 = -0.78; V5 = 0.91; V6 = -0.11
  V7 = 0.22; V8 = -0.43; V9 = 0.65; V10 = -0.87; V11 = 0.14; V12 = -0.25
  V13 = 0.36; V14 = -0.47; V15 = 0.58; V16 = -0.69; V17 = 0.71; V18 = -0.82
  V19 = 0.93; V20 = -0.15; V21 = 0.26; V22 = -0.37; V23 = 0.48; V24 = -0.59
  V25 = 0.61; V26 = -0.72; V27 = 0.83; V28 = -0.94
}
$prediction = Invoke-RestMethod "$base/api/v1/predict" -Method Post -Headers $json -Body ($fraudSample | ConvertTo-Json)
$prediction
$transactionId = $prediction.transaction_id
```

### ML-path sample: normal transaction

This removes the explicit rule trigger. The model determines whether the
transaction is approved or rejected.

```powershell
$normalSample = $fraudSample.Clone()
$normalSample.Amount = 42.50
$normalSample.is_blacklisted_device = 0
$normalPrediction = Invoke-RestMethod "$base/api/v1/predict" -Method Post -Headers $json -Body ($normalSample | ConvertTo-Json)
$normalPrediction
```

### Submit analyst feedback

Use the `transaction_id` from a successful prediction. `1` means confirmed
fraud and `0` means legitimate / false positive.

```powershell
Invoke-RestMethod "$base/api/v1/transactions/$transactionId/feedback" -Method Post -Headers $json -Body (@{
  confirmed_label = 1
} | ConvertTo-Json)
```

## Route checklist

| Method | Route | Sample data |
|---|---|---|
| GET | `/` | none |
| GET | `/health` | none |
| POST | `/api/v1/auth/login` | email, password |
| POST | `/api/v1/auth/logout` | Bearer token |
| POST | `/api/v1/auth/forgot-password` | email |
| POST | `/api/v1/auth/reset-password` | token, password |
| GET | `/api/v1/users` | admin Bearer token |
| POST | `/api/v1/users` | name, email, password, role |
| PATCH | `/api/v1/users/{user_id}` | name, role, active |
| DELETE | `/api/v1/users/{user_id}` | admin Bearer token |
| POST | `/api/v1/users/{user_id}/reset-password` | password |
| GET | `/api/v1/transactions` | none |
| POST | `/api/v1/predict` | Time, Amount, V1–V28 |
| POST | `/api/v1/transactions/{transaction_id}/feedback` | confirmed_label: 0 or 1 |

The separate `backend/standalone_user_api.py` service uses different routes,
JWT fields, roles, and port 8001; this document does not mix those contracts
with the frontend-connected API. For the standalone service, the access token
must be sent explicitly on every protected request:

If you do not know the current port-8001 admin password, use the development
reset flow before logging in:

1. Call `POST /api/v1/auth/forgot-password` with:

   ```json
   {
     "email": "admin@example.com"
   }
   ```

2. Copy the `development_reset_token` from the response.
3. Call `POST /api/v1/auth/reset-password` with:

   ```json
   {
     "token": "PASTE_DEVELOPMENT_RESET_TOKEN_HERE",
     "password": "New-Admin-Password-2026!"
   }
   ```

4. Log in with `admin@example.com` and `New-Admin-Password-2026!`.

The Argon2 value stored in the database is a one-way password hash; it cannot
be decoded to recover the old password. The development reset token should
not be exposed or enabled in production.

Start the standalone service in a separate terminal and keep that terminal
running while using Swagger:

```powershell
.\.venv\Scripts\python.exe -m uvicorn backend.standalone_user_api:app --host 127.0.0.1 --port 8001 --reload
```

Verify that `http://127.0.0.1:8001/health` opens successfully before opening
`http://127.0.0.1:8001/docs`.

```powershell
$standaloneBase = "http://127.0.0.1:8001"
$accessToken = "PASTE_ACCESS_TOKEN_FROM_LOGIN_HERE"
$standaloneAuth = @{ Authorization = "Bearer $accessToken"; Accept = "application/json" }

Invoke-RestMethod "$standaloneBase/api/v1/users?skip=0&limit=50&is_active=true" -Headers $standaloneAuth
```

Equivalent cURL:

```bash
curl -X GET "http://127.0.0.1:8001/api/v1/users?skip=0&limit=50&is_active=true" \
  -H "Accept: application/json" \
  -H "Authorization: Bearer PASTE_ACCESS_TOKEN_FROM_LOGIN_HERE"
```

In Swagger UI for port 8001, click **Authorize**, enter the access-token value
(without manually adding `Bearer`), and click **Authorize** again. Swagger
will then generate the `Authorization: Bearer <access_token>` header for
protected endpoints. Refresh the `/docs` page after restarting the API if the
Authorize button is not visible.
