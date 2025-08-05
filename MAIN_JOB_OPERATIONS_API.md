# Main Job Operations API Documentation

## Overview

This API provides endpoints for managing main jobs and their operations within weekly reports. Each main job represents a primary task or project for a specific week, and contains multiple operations (steps) that detail the work performed.

## Authentication

All endpoints require JWT authentication. Include the token in the Authorization header:
```
Authorization: Bearer <your_jwt_token>
```

## Data Structure

### Main Job with Operations
```json
{
  "main_job": {
    "id": 1,
    "weekly_report": 1,
    "title": "Main Job Title",
    "operations": [
      {
        "id": 1,
        "step_number": 1,
        "operation_description": "Description of the operation step",
        "tools_used": "Tools, machinery, equipment used"
      }
    ]
  }
}
```

## Endpoints

### 1. GET /reports/main-jobs/{mainJobId}/operations/

**Description:** Fetch all operations for a specific main job.

**URL Parameters:**
- `mainJobId` (integer): ID of the main job

**Response:**
```json
[
  {
    "id": 1,
    "step_number": 1,
    "operation_description": "Setup and preparation",
    "tools_used": "Screwdriver, Multimeter, Safety gloves",
    "created_at": "2025-01-15T10:30:00Z",
    "updated_at": "2025-01-15T10:30:00Z"
  },
  {
    "id": 2,
    "step_number": 2,
    "operation_description": "Component assembly",
    "tools_used": "Soldering iron, Wire stripper, Heat shrink",
    "created_at": "2025-01-15T10:35:00Z",
    "updated_at": "2025-01-15T10:35:00Z"
  }
]
```

**Status Codes:**
- `200 OK`: Operations retrieved successfully
- `404 Not Found`: Main job not found
- `401 Unauthorized`: Invalid or missing authentication

---

### 2. POST /reports/main-jobs/{mainJobId}/operations/

**Description:** Create a new operation for a specific main job.

**URL Parameters:**
- `mainJobId` (integer): ID of the main job

**Request Body:**
```json
{
  "step_number": 1,
  "operation_description": "Setup and preparation",
  "tools_used": "Screwdriver, Multimeter, Safety gloves"
}
```

**Response:**
```json
{
  "id": 1,
  "step_number": 1,
  "operation_description": "Setup and preparation",
  "tools_used": "Screwdriver, Multimeter, Safety gloves",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:30:00Z"
}
```

**Status Codes:**
- `201 Created`: Operation created successfully
- `400 Bad Request`: Invalid data or validation errors
- `404 Not Found`: Main job not found
- `401 Unauthorized`: Invalid or missing authentication

**Validation Rules:**
- `step_number`: Must be positive integer
- `step_number`: Must be unique within the main job
- `operation_description`: Required field
- `tools_used`: Optional field

---

### 3. PUT /reports/main-jobs/{mainJobId}/operations/{operationId}/

**Description:** Update an existing operation.

**URL Parameters:**
- `mainJobId` (integer): ID of the main job
- `operationId` (integer): ID of the operation to update

**Request Body:**
```json
{
  "step_number": 1,
  "operation_description": "Setup and preparation (UPDATED)",
  "tools_used": "Screwdriver, Multimeter, Safety gloves, Wire stripper"
}
```

**Response:**
```json
{
  "id": 1,
  "step_number": 1,
  "operation_description": "Setup and preparation (UPDATED)",
  "tools_used": "Screwdriver, Multimeter, Safety gloves, Wire stripper",
  "created_at": "2025-01-15T10:30:00Z",
  "updated_at": "2025-01-15T10:35:00Z"
}
```

**Status Codes:**
- `200 OK`: Operation updated successfully
- `400 Bad Request`: Invalid data or validation errors
- `404 Not Found`: Main job or operation not found
- `401 Unauthorized`: Invalid or missing authentication

---

### 4. DELETE /reports/main-jobs/{mainJobId}/operations/{operationId}/

**Description:** Delete an operation.

**URL Parameters:**
- `mainJobId` (integer): ID of the main job
- `operationId` (integer): ID of the operation to delete

**Response:**
- No content

**Status Codes:**
- `204 No Content`: Operation deleted successfully
- `404 Not Found`: Main job or operation not found
- `401 Unauthorized`: Invalid or missing authentication

---

### 5. PUT /reports/main-jobs/{mainJobId}/

**Description:** Update the main job title.

**URL Parameters:**
- `mainJobId` (integer): ID of the main job

**Request Body:**
```json
{
  "title": "Updated Main Job Title"
}
```

**Response:**
```json
{
  "id": 1,
  "weekly_report": 1,
  "title": "Updated Main Job Title",
  "operations": [
    {
      "id": 1,
      "step_number": 1,
      "operation_description": "Setup and preparation",
      "tools_used": "Screwdriver, Multimeter, Safety gloves",
      "created_at": "2025-01-15T10:30:00Z",
      "updated_at": "2025-01-15T10:30:00Z"
    }
  ]
}
```

**Status Codes:**
- `200 OK`: Main job updated successfully
- `400 Bad Request`: Invalid data or validation errors
- `404 Not Found`: Main job not found
- `401 Unauthorized`: Invalid or missing authentication

**Validation Rules:**
- `title`: Cannot be empty if provided

---

## Error Responses

### Validation Error
```json
{
  "step_number": ["Step number must be positive."],
  "operation_description": ["This field is required."]
}
```

### Not Found Error
```json
{
  "detail": "Not found."
}
```

### Unauthorized Error
```json
{
  "detail": "Authentication credentials were not provided."
}
```

---

## Usage Examples

### Frontend Integration

#### 1. Fetch Operations
```javascript
const fetchOperations = async (mainJobId) => {
  const response = await fetch(`/api/reports/main-jobs/${mainJobId}/operations/`, {
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    }
  });
  return response.json();
};
```

#### 2. Create Operation
```javascript
const createOperation = async (mainJobId, operationData) => {
  const response = await fetch(`/api/reports/main-jobs/${mainJobId}/operations/`, {
    method: 'POST',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(operationData)
  });
  return response.json();
};
```

#### 3. Update Operation
```javascript
const updateOperation = async (mainJobId, operationId, operationData) => {
  const response = await fetch(`/api/reports/main-jobs/${mainJobId}/operations/${operationId}/`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify(operationData)
  });
  return response.json();
};
```

#### 4. Delete Operation
```javascript
const deleteOperation = async (mainJobId, operationId) => {
  const response = await fetch(`/api/reports/main-jobs/${mainJobId}/operations/${operationId}/`, {
    method: 'DELETE',
    headers: {
      'Authorization': `Bearer ${token}`
    }
  });
  return response.status === 204;
};
```

#### 5. Update Main Job Title
```javascript
const updateMainJobTitle = async (mainJobId, title) => {
  const response = await fetch(`/api/reports/main-jobs/${mainJobId}/`, {
    method: 'PUT',
    headers: {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json'
    },
    body: JSON.stringify({ title })
  });
  return response.json();
};
```

---

## Testing

Run the test script to verify all endpoints:

```bash
python test_main_job_operations.py
```

This will test all CRUD operations for main jobs and their operations.

---

## Notes

1. **Authorization**: All endpoints require authentication and users can only access their own data
2. **Step Numbers**: Must be unique within a main job
3. **Ordering**: Operations are returned ordered by step_number
4. **Validation**: All fields are validated before saving
5. **Cascade**: Deleting a main job will delete all its operations
6. **Relationships**: Operations are linked to main jobs, which are linked to weekly reports 