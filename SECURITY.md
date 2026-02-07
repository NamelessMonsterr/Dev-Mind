# DevMind Security Documentation

## Overview

DevMind implements enterprise-grade security measures including multi-user authentication, role-based access control (RBAC), workspace isolation, and comprehensive security hardening.

## Authentication & Authorization

### User Authentication

**Method**: JWT (JSON Web Tokens)

- **Access Tokens**: Short-lived (30 minutes), used for API authentication
- **Refresh Tokens**: Long-lived (7 days), stored in database for revocation
- **Token Rotation**: New refresh token issued on each refresh request
- **Secure Storage**: Refresh tokens stored in PostgreSQL with user relationship

**Password Security**:

- Algorithm: bcrypt with cost factor 12
- Minimum length: 12 characters
- Complexity requirements:
  - At least one uppercase letter
  - At least one lowercase letter
  - At least one digit
  - At least one special character

**Account Protection**:

- Account lockout after 5 failed login attempts
- Lockout duration: 15 minutes
- Failed attempts counter reset on successful login

### Role-Based Access Control (RBAC)

**Global Roles** (User level):

- `admin`: Full system access
- `user`: Standard user access
- `viewer`: Read-only access

**Workspace Roles** (Workspace level):

- `owner`: Full workspace control, can delete workspace
- `admin`: Can manage workspace settings and members
- `member`: Can use workspace resources
- `viewer`: Read-only workspace access

### Multi-Tenancy (Workspaces)

**Isolation**: All resources (indices, jobs, sessions) are scoped by `workspace_id`

**Membership**: Users can belong to multiple workspaces with different roles

**Permissions**:

- Workspace access verified on every request
- Role-based permissions enforced via FastAPI dependencies
- Owner-only operations: workspace deletion
- Admin/Owner operations: member management, workspace settings

## API Security

### Endpoints & Authentication

**Public Endpoints** (No authentication required):

- `POST /auth/register` - User registration
- `POST /auth/login` - User login
- `POST /auth/refresh` - Token refresh
- `GET /health` - Health check

**Protected Endpoints** (Requires authentication):

- All `/auth/me`, `/auth/logout`, `/auth/change-password`
- All `/workspaces/*` endpoints
- All `/ingest/*`, `/search/*`, `/chat/*`, `/embed/*` endpoints

**Workspace-Scoped Endpoints**:

- All operations on indices, jobs, and sessions require workspace access
- Workspace ID verified via `verify_workspace_access` dependency

### CORS Configuration

**Configurable Origins**: Set via `ALLOWED_ORIGINS` environment variable

**Default**: `http://localhost:3000` (development)

**Production**: Should be set to specific domains (e.g., `https://devmind.yourdomain.com`)

**Settings**:

```python
allow_credentials=True  # Required for cookies/auth headers
allow_methods=["*"]     # All HTTP methods
allow_headers=["*"]     # All headers
```

## Database Security

**Engine**: PostgreSQL with SQLAlchemy ORM

**Connection**: Parameterized queries prevent SQL injection

**Security Measures**:

- UUID primary keys (non-sequential, harder to enumerate)
- Foreign key constraints with CASCADE delete
- Unique constraints (email, username, workspace slug)
- Indexed columns for performance

**Password Storage**:

- Never stored in plain text
- Bcrypt hashing with salt
- Hash verification via constant-time comparison

## Security Headers

**Implemented** (via middleware):

- `X-Content-Type-Options: nosniff` - Prevent MIME sniffing
- `X-Frame-Options: DENY` - Prevent clickjacking
- `X-XSS-Protection: 1; mode=block` - XSS protection (legacy browsers)
- `Strict-Transport-Security` - Force HTTPS (production only)

**Recommended** (to be implemented):

- Content Security Policy (CSP)
- Referrer-Policy
- Permissions-Policy

## Input Validation

**Pydantic Models**: All API requests validated via Pydantic schemas

**Validation Rules**:

- Email format validation
- Username pattern: `[a-zA-Z0-9_-]+`
- Workspace slug pattern: `[a-z0-9-]+`
- Max lengths enforced on all string fields
- Required fields enforced

**SQL Injection Protection**:

- SQLAlchemy ORM used for all queries
- No raw SQL queries with user input
- Parameterized queries only

**XSS Protection**:

- API returns JSON only (no HTML rendering)
- Frontend responsible for output encoding

## Rate Limiting

**Current Status**: Not implemented

**Recommendation**: Implement rate limiting on:

- `/auth/login` - Prevent brute force (e.g., 5 attempts/minute)
- `/auth/register` - Prevent spam (e.g., 3 accounts/hour)
- `/auth/refresh` - Prevent token abuse (e.g., 10 refreshes/minute)

**Implementation Options**:

- `slowapi` Python package
- Nginx rate limiting
- Cloud provider WAF rules

## Secrets Management

**Required Secrets**:

- `JWT_SECRET_KEY`: Used for signing JWT tokens (CRITICAL)
- `DATABASE_URL`: PostgreSQL connection string
- LLM API keys (OpenAI, Anthropic, etc.)

**Storage**:

- ✅ Environment variables (.env file)
- ✅ Never committed to version control (.env in .gitignore)
- 🔲 Production: Use managed secrets (AWS Secrets Manager, HashiCorp Vault)

**Rotation**:

- JWT secret should be rotated periodically
- Database passwords should be rotated quarterly
- API keys should be monitored for leaks

## Threat Model

### Identified Threats

1. **Brute Force Attacks**: ✅ Mitigated by account lockout
2. **Token Theft**: ✅ Mitigated by short token expiry + refresh rotation
3. **SQL Injection**: ✅ Mitigated by ORM + parameterized queries
4. **XSS**: ✅ Mitigated by JSON-only API (frontend handles encoding)
5. **CSRF**: 🔲 Not yet implemented (recommend SameSite cookies)
6. **Workspace Enumeration**: ✅ Mitigated by UUID + access checks
7. **Privilege Escalation**: ✅ Mitigated by RBAC enforcement

### Unmitigated Risks

1. **Rate Limiting**: No rate limiting implemented
2. **CSRF**: No CSRF tokens for state-changing operations
3. **File Upload Security**: File ingestion should validate file types/sizes
4. **Audit Logging**: No security event logging
5. **Session Management**: No concurrent session limits

## Security Testing

**Implemented Tests** (`tests/test_auth.py`):

- Registration validation
- Login authentication
- Account lockout mechanism
- JWT token management
- Password strength validation
- Refresh token rotation

**Missing Tests**:

- RBAC enforcement across all endpoints
- Workspace isolation verification
- SQL injection attempts
- XSS payload handling
- Rate limit enforcement

## Incident Response

**Current Status**: No formal incident response plan

**Recommended Steps**:

1. Detect: Monitor logs for suspicious activity
2. Contain: Ability to quickly revoke tokens, disable accounts
3. Investigate: Audit trails for all security events
4. Recover: Database backups, rollback procedures
5. Learn: Post-mortem documentation

## Compliance

**Data Protection**:
-Storage: User data stored in PostgreSQL

- Encryption at rest: Database-level encryption (configure in PostgreSQL)
- Encryption in transit: HTTPS/TLS (configure in reverse proxy)

**GDPR Considerations**:

- User data deletion: Cascade deletes implemented
- Data export: Not yet implemented
- Consent tracking: Not applicable (B2B tool)

## Security Checklist

### Pre-Production

- [ ] Change JWT_SECRET_KEY from default
- [ ] Set strong DATABASE_URL password
- [ ] Configure ALLOWED_ORIGINS for production domain
- [ ] Enable HTTPS in production (Traefik/nginx)
- [ ] Set up security headers middleware
- [ ] Implement rate limiting
- [ ] Add CSRF protection
- [ ] Set up audit logging
- [ ] Configure database backups
- [ ] Review all default credentials

### Post-Deployment

- [ ] Monitor failed login attempts
- [ ] Review access logs weekly
- [ ] Rotate JWT secret quarterly
- [ ] Update dependencies monthly (security patches)
- [ ] Conduct security testing
- [ ] Review workspace permissions
- [ ] Audit admin/owner accounts

## Reporting Security Issues

**Contact**: [Your security contact email]

**Response Time**: 24-48 hours

**Disclosure**: Responsible disclosure requested (90 days)

---

**Last Updated**: 2026-02-07  
**Version**: 1.0  
**Reviewer**: DevMind Security Team
