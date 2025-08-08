# Billing System API Documentation

## Overview

The billing system manages user token balances, payment transactions, and AI enhancement usage tracking. Users start with 400 free trial tokens and must subscribe to continue using AI enhancements.

## Models

### UserBalance
- **available_tokens**: Current token balance (default: 400)
- **payment_status**: FREE_TRIAL, UNSUBSCRIBED, SUBSCRIBED
- **tokens_used**: Total tokens consumed
- **created_at/updated_at**: Timestamps

### Transaction
- **user**: Associated user
- **user_phone_number**: Payment phone number
- **sender_name**: Name of person who sent payment
- **payment_method**: DIRECT or WAKALA (money agent)
- **wakala_name**: Agent name (if using wakala)
- **transaction_status**: PENDING, APPROVED, REJECTED
- **amount**: Payment amount
- **tokens_generated**: Tokens calculated (amount × 0.3)
- **confirmed_by**: Staff member who approved
- **created_at/updated_at**: Timestamps

## API Endpoints

### 1. User Balance Management

#### Get User Balance
```
GET /api/billing/balance/my_balance/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "id": 1,
    "user": "john_doe",
    "user_full_name": "John Doe",
    "available_tokens": 400,
    "payment_status": "FREE_TRIAL",
    "tokens_used": 0,
    "can_use_ai": true,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

### 2. Transaction Management

#### Create Transaction (User)
```
POST /api/billing/transactions/
```

**Request Body:**
```json
{
  "user_phone_number": "0712345678",
  "sender_name": "John Doe",
  "payment_method": "DIRECT",
  "amount": 1000.00
}
```

**Response:**
```json
{
  "success": true,
  "message": "Transaction created successfully. Please wait for approval.",
  "data": {
    "id": 1,
    "user": "john_doe",
    "user_full_name": "John Doe",
    "user_phone_number": "0712345678",
    "sender_name": "John Doe",
    "payment_method": "DIRECT",
    "wakala_name": null,
    "transaction_status": "PENDING",
    "amount": "1000.00",
    "tokens_generated": 0,
    "confirmed_by_name": null,
    "created_at": "2024-01-15T10:30:00Z",
    "updated_at": "2024-01-15T10:30:00Z"
  }
}
```

#### Verify Payment Details
```
POST /api/billing/transactions/{transaction_id}/verify_payment/
```

**Request Body:**
```json
{
  "user_phone_number": "0712345678",
  "sender_name": "John Doe",
  "amount": 1000.00
}
```

### 3. Staff Transaction Management

#### Create Transaction (Staff)
```
POST /api/billing/staff/transactions/
```

**Request Body:**
```json
{
  "user_id": 1,
  "user_phone_number": "0712345678",
  "sender_name": "John Doe",
  "payment_method": "WAKALA",
  "wakala_name": "M-Pesa Agent",
  "amount": 1000.00
}
```

#### Get Pending Transactions
```
GET /api/billing/staff/transactions/pending_transactions/
```

#### Approve Transaction
```
POST /api/billing/staff/transactions/{transaction_id}/approve_transaction/
```

#### Reject Transaction
```
POST /api/billing/staff/transactions/{transaction_id}/reject_transaction/
```

### 4. Token Usage Tracking

#### Track AI Enhancement Usage
```
POST /api/billing/token-usage/track_usage/
```

**Request Body:**
```json
{
  "usage_type": "FULLFILLED",
  "weekly_report_id": 1
}
```

**Usage Types:**
- **FULLFILLED**: 5 days filled (300 tokens)
- **PARTIAL**: 3-4 days filled (400 tokens)
- **EMPTY**: less than 3 days (500 tokens)

**Response:**
```json
{
  "success": true,
  "message": "AI enhancement used. 300 tokens deducted.",
  "remaining_tokens": 100,
  "usage_type": "FULLFILLED",
  "tokens_deducted": 300
}
```

#### Get Usage History
```
GET /api/billing/token-usage/usage_history/
```

### 5. Billing Dashboard

#### Get Dashboard Data
```
GET /api/billing/dashboard/dashboard_data/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "balance": {
      "available_tokens": 100,
      "payment_status": "SUBSCRIBED",
      "tokens_used": 300
    },
    "recent_transactions": [...],
    "pending_transactions": 0,
    "total_spent": 1000.00,
    "can_use_ai": true
  }
}
```

#### Get Payment Information
```
GET /api/billing/dashboard/payment_info/
```

**Response:**
```json
{
  "success": true,
  "data": {
    "payment_number": "0712345678",
    "payment_instructions": [
      "Send money to the provided number",
      "Use your name as sender name",
      "Submit transaction details after payment",
      "Wait for staff approval"
    ],
    "token_calculation": "Tokens = Amount × 0.3",
    "usage_costs": {
      "fullfilled": "300 tokens (5 days filled)",
      "partial": "400 tokens (3-4 days filled)",
      "empty": "500 tokens (less than 3 days)"
    }
  }
}
```

## Business Logic

### Token Calculation
- **Formula**: `Tokens = Amount × 0.3`
- **Example**: 1000 TZS = 300 tokens

### Payment Flow
1. User creates transaction with payment details
2. User makes manual payment to provided number
3. User submits verification details
4. Staff approves transaction
5. Tokens are added to user balance
6. User status changes to SUBSCRIBED

### Staff Initialization Flow
1. Staff creates transaction on behalf of user
2. User makes payment and forgets to submit details
3. User later submits exact details
4. System auto-approves if details match
5. Tokens are added to user balance

### AI Enhancement Usage
- **Free Trial**: 400 tokens, can use AI enhancement
- **Subscribed**: Can use AI enhancement if tokens available
- **Unsubscribed**: Cannot use AI enhancement

### Token Deduction Logic
- **5 days filled**: 300 tokens (FULLFILLED)
- **3-4 days filled**: 400 tokens (PARTIAL)
- **Less than 3 days**: 500 tokens (EMPTY)

## Error Responses

### Insufficient Tokens
```json
{
  "success": false,
  "message": "Insufficient tokens or not subscribed. Please top up your account.",
  "available_tokens": 50,
  "payment_status": "UNSUBSCRIBED"
}
```

### Validation Error
```json
{
  "success": false,
  "errors": {
    "wakala_name": ["Wakala name is required when using money agent payment method."]
  }
}
```

### Staff Access Required
```json
{
  "success": false,
  "message": "Staff access required"
}
```

## Integration with AI Enhancement

The billing system integrates with the AI enhancement system in the reports app. When a user requests AI enhancement:

1. System checks if user can use AI enhancement
2. Calculates token cost based on report completion
3. Deducts tokens if sufficient balance
4. Proceeds with AI enhancement
5. Returns error if insufficient tokens

## Security Features

- JWT authentication required for all endpoints
- Staff-only endpoints for transaction management
- User can only access their own transactions
- Validation for payment method and wakala name
- Automatic balance creation for new users

## Usage Examples

### Frontend Integration

```javascript
// Check if user can use AI enhancement
const checkBalance = async () => {
  const response = await fetch('/api/billing/balance/my_balance/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  const data = await response.json();
  return data.data.can_use_ai;
};

// Track AI enhancement usage
const trackUsage = async (weeklyReportId, usageType) => {
  const response = await fetch('/api/billing/token-usage/track_usage/', {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({
      weekly_report_id: weeklyReportId,
      usage_type: usageType
    })
  });
  return response.json();
};
```

### Staff Management

```javascript
// Get pending transactions
const getPendingTransactions = async () => {
  const response = await fetch('/api/billing/staff/transactions/pending_transactions/', {
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};

// Approve transaction
const approveTransaction = async (transactionId) => {
  const response = await fetch(`/api/billing/staff/transactions/${transactionId}/approve_transaction/`, {
    method: 'POST',
    headers: { 'Authorization': `Bearer ${token}` }
  });
  return response.json();
};
```

