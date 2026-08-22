# MIPT Backend API Documentation

## Base URL
- Production: `https://mipt.pythonanywhere.com/api`
- Development: `http://localhost:8000/api`

## Authentication
All endpoints (except registration and login) require JWT authentication via `Authorization: Bearer <access_token>` header.

## Authentication Endpoints

### POST /auth/register/
Register a new user account.

**Request Body:**
```json
{
  "username": "string",
  "email": "string",
  "first_name": "string",
  "last_name": "string",
  "password": "string",
  "password_confirm": "string"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Registration successful"
}
```

### POST /auth/login/
Login with username and password.

**Request Body:**
```json
{
  "username": "string",
  "password": "string"
}
```

**Response:**
```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user": {
    "id": 1,
    "username": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string"
  }
}
```

### POST /auth/google-auth/
Authenticate with Google OAuth2.

**Request Body:**
```json
{
  "id_token": "google_id_token"
}
```

**Response:**
```json
{
  "access": "jwt_access_token",
  "refresh": "jwt_refresh_token",
  "user": {
    "id": 1,
    "username": "string",
    "email": "string",
    "first_name": "string",
    "last_name": "string",
    "full_name": "string",
    "picture": "string"
  },
  "is_new_user": false
}
```

### POST /auth/refresh/
Refresh JWT access token.

**Request Body:**
```json
{
  "refresh": "jwt_refresh_token"
}
```

**Response:**
```json
{
  "access": "new_jwt_access_token",
  "refresh": "new_jwt_refresh_token"
}
```

### POST /auth/logout/
Logout current user (client-side token removal).

**Response:**
```json
{
  "success": true,
  "message": "Logged out successfully"
}
```

## User Profile Endpoints

### GET /auth/profile/
Get current user's profile.

**Response:**
```json
{
  "id": 1,
  "user": 1,
  "student_id": "string",
  "college": "CoET|CoICT|SoMG",
  "program": "MECHANICAL|ELECTRICAL|CIVIL|...",
  "year_of_study": 1,
  "pt_phase": "PT1|PT2|PT3",
  "department": "string",
  "supervisor_name": "string",
  "supervisor_email": "string",
  "phone_number": "string",
  "company_name": "string",
  "company_region": "string",
  "profile_picture": "string",
  "created_at": "2024-01-01T00:00:00Z",
  "updated_at": "2024-01-01T00:00:00Z",
  "user_details": {
    "username": "string",
    "email": "string",
    "full_name": "string"
  }
}
```

### PUT /auth/profile/
Update current user's profile.

**Request Body:**
```json
{
  "student_id": "string",
  "college": "CoET",
  "program": "MECHANICAL",
  "year_of_study": 2,
  "pt_phase": "PT2",
  "department": "string",
  "supervisor_name": "string",
  "supervisor_email": "string",
  "phone_number": "string",
  "company_name": "string",
  "company_region": "string"
}
```

**Response:**
```json
{
  "id": 1,
  "user": 1,
  "student_id": "string",
  "college": "CoET",
  "program": "MECHANICAL",
  ...
}
```

### POST /auth/profile/upload-picture/
Upload profile picture.

**Request:** `multipart/form-data` with `profile_picture` file.

**Response:**
```json
{
  "success": true,
  "message": "Profile picture uploaded successfully",
  "profile_picture_url": "http://example.com/media/profile_pictures/image.jpg"
}
```

### DELETE /auth/profile/remove-picture/
Remove profile picture.

**Response:**
```json
{
  "success": true,
  "message": "Profile picture removed successfully"
}
```

## College and Program Choices

### Colleges:
- `CoET` - College of Engineering and Technology
- `CoICT` - College of Information and Communication Technologies
- `SoMG` - School of Mining and Geosciences

### Programs by College:

**CoET Programs:**
- `MECHANICAL` - BSc. Mechanical Engineering
- `ELECTRICAL` - BSc. Electrical Engineering
- `CIVIL` - BSc. Civil Engineering
- `TEXTILE_DESIGN` - BSc. Textile Design
- `TEXTILE_ENGINEERING` - BSc. Textile Engineering
- `INDUSTRIAL` - BSc. Industrial Engineering
- `GEOMATIC` - BSc. Geomatic Engineering
- `CHEMICAL` - BSc. Chemical Engineering
- `ARCHITECTURE` - Bachelor of Architecture
- `QUANTITY_SURVEYING` - Bachelor of Science in Quantity Surveying

**CoICT Programs:**
- `COMPUTER` - BSc in Computer Science
- `ELECTRONIC_SCIENCE` - BSc in Electronic Science and Communication
- `COMPUTER_ENGINEERING` - BSc in Computer Engineering and Information Technology
- `TELECOMMUNICATIONS` - BSc in Telecommunications Engineering
- `BUSINESS_IT` - BSc in Business Information Technology
- `ELECTRONIC_ENGINEERING` - BSc in Electronic Engineering

**SoMG Programs:**
- `MINING` - BSc in Mining Engineering
- `GEOLOGY_GEOTHERMAL` - BSc in Geology and Geothermal Resources
- `PETROLEUM_GEOLOGY` - BSc in Petroleum Geology
- `GEOLOGY` - BSc in Geology
- `GEOLOGY_WITH` - BSc with Geology
- `ENGINEERING_GEOLOGY` - BSc in Engineering Geology
- `METALLURGY_MINERAL` - BSc in Metallurgy and Mineral Processing Engineering
- `PETROLEUM` - BSc in Petroleum Engineering
- `GEOPHYSICS` - BSc in Geophysics

## Report Export Endpoints

### GET /export/weekly-report/pdf/{weekly_report_id}/
Export weekly report as PDF.

**Response:** PDF file download

### GET /export/weekly-report/docx/{weekly_report_id}/
Export weekly report as DOCX.

**Response:** DOCX file download

### POST /export/all-weekly-reports/
Export all weekly reports as combined logbook.

**Request Body:**
```json
{
  "type": "pdf|docx",
  "force_export": false
}
```

**Response:** PDF or DOCX file download

## Billing Endpoints

### GET /billing/my-balance/
Get current user's token balance.

**Response:**
```json
{
  "success": true,
  "data": {
    "available_tokens": 100,
    "total_tokens_earned": 500,
    "total_tokens_spent": 400
  }
}
```

### POST /billing/transactions/
Create a new transaction.

**Request Body:**
```json
{
  "user_phone_number": "string",
  "sender_name": "string",
  "amount": 1000,
  "payment_method": "DIRECT"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Transaction created successfully. Please wait for approval.",
  "data": {
    "id": 1,
    "amount": 1000,
    "transaction_status": "PENDING"
  }
}
```

## Error Responses

All endpoints return error responses in the following format:

```json
{
  "success": false,
  "message": "User-friendly error message",
  "errors": {
    "field": ["error details"]
  }
}
```

### Common HTTP Status Codes:
- `200` - Success
- `201` - Created
- `400` - Bad Request
- `401` - Unauthorized
- `403` - Forbidden
- `404` - Not Found
- `500` - Internal Server Error

## SMS Notifications

The system sends SMS notifications to admin phone number (0614021404) for:
- New user registrations
- Zero token export attempts
- Transaction submissions

SMS service uses BEEM Africa API with detailed logging for debugging.
