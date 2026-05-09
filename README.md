# Authentication API Documentation

## Base URL
```
http://localhost:8000
```

## Endpoints

### 1. User Registration
**POST** `/api/auth/register/`

Register a new user account.

**Request Body:**
```json
{
    "first_name": "John",
    "last_name": "Doe", 
    "username": "johndoe",
    "email": "john.doe@example.com",
    "password": "password123"
}
```

**Success Response (201):**
```json
{
    "message": "User registered successfully",
    "user_id": 1
}
```

**Error Response (400):**
```json
{
    "validation_error": true,
    "errors": {
        "username": "Username already exists",
        "email": "Email already exists"
    }
}
```

### 2. User Login
**POST** `/api/auth/login/`

Authenticate user with username/email and password.

**Request Body:**
```json
{
    "username_or_email": "johndoe",
    "password": "password123"
}
```

**Success Response (200):**
```json
{
    "message": "Login successful",
    "user": {
        "id": 1,
        "username": "johndoe",
        "email": "john.doe@example.com",
        "first_name": "John",
        "last_name": "Doe"
    }
}
```

**Error Response (401):**
```json
{
    "error": "Invalid credentials"
}
```

### 3. Check User Existence
**POST** `/api/auth/check-user/`

Check if username or email already exists.

**Request Body:**
```json
{
    "username": "johndoe",
    "email": "john.doe@example.com"
}
```

**Response (200):**
```json
{
    "exists": true,
    "errors": {
        "username": "Username already exists"
    }
}
```

### 4. Reset Password Request
**POST** `/api/auth/reset-password/`

Send OTP to user's email for password reset.

**Request Body:**
```json
{
    "email": "john.doe@example.com"
}
```

**Success Response (200):**
```json
{
    "message": "OTP sent to your email"
}
```

**Error Response (404):**
```json
{
    "error": "Email not found"
}
```

### 5. Confirm Password Reset
**POST** `/api/auth/confirm-reset/`

Reset password using OTP verification.

**Request Body:**
```json
{
    "email": "john.doe@example.com",
    "otp": "123456",
    "new_password": "newpassword123"
}
```

**Success Response (200):**
```json
{
    "message": "Password reset successfully"
}
```

**Error Response (400):**
```json
{
    "error": "Invalid or expired OTP"
}
```

## Common Error Responses

### Validation Error (400)
```json
{
    "validation_error": true,
    "errors": {
        "field_name": "Error message"
    }
}
```

### Server Error (500)
```json
{
    "error": "Server error"
}
```

### Invalid JSON (400)
```json
{
    "error": "Invalid JSON"
}
```

## Request Headers
```
Content-Type: application/json
```

## Validation Rules

- **Password:** Minimum 8 characters
- **Email:** Must contain @ symbol
- **OTP:** Valid for 10 minutes
- **All fields:** Required for registration