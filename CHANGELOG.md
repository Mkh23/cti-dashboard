# Changelog

## [Unreleased]

### Fixed
- **Auth Registration Issue**: Fixed the registration endpoint to properly handle cases where database roles aren't seeded
  - Added defensive checks for `admin_role` and `technician_role` before attempting to assign them
  - Returns clear error message "Database not properly initialized. Please run migrations: alembic upgrade head" if roles are missing
  - Prevents `AttributeError: 'NoneType' object has no attribute 'id'` when roles don't exist

### Added
- **Comprehensive Test Suite**: Added 14 tests with 70%+ code coverage
  - Auth endpoint tests (12 tests): registration, login, /me endpoint, role assignment
  - Health check tests (2 tests): /healthz and /readyz endpoints
  - Test infrastructure using pytest with PostgreSQL test database
  - Test fixtures for database isolation and role seeding control
  
- **Documentation**:
  - Added `api/README.md` with setup instructions, API documentation, and troubleshooting
  - Added `TESTING.md` with comprehensive testing documentation
  - Updated main `README.md` with testing section and improved setup instructions
  - Updated `ROADMAP.md` to reflect completed work

- **Test Dependencies**: Added pytest, pytest-cov, and httpx to requirements.txt

### Changed
- **Improved Code Quality**: Auth module now has 100% test coverage
- **Better Error Messages**: Registration failure provides actionable error message with fix instructions
- **Defensive Programming**: Added validation checks before attempting to assign roles

### Technical Details

#### Before
```python
admin_role = db.query(Role).filter_by(name="admin").first()  # Could be None
any_admin = db.query(UserRole).join(Role).filter(Role.name=="admin").first()
role_to_assign = admin_role if not any_admin else db.query(Role).filter_by(name="technician").first()
db.add(UserRole(user_id=user.id, role_id=role_to_assign.id))  # Would fail if role_to_assign is None
```

#### After
```python
admin_role = db.query(Role).filter_by(name="admin").first()
technician_role = db.query(Role).filter_by(name="technician").first()

if not admin_role or not technician_role:
    raise HTTPException(
        status_code=500,
        detail="Database not properly initialized. Please run migrations: alembic upgrade head"
    )

any_admin = db.query(UserRole).join(Role).filter(Role.name=="admin").first()
role_to_assign = admin_role if not any_admin else technician_role
db.add(UserRole(user_id=user.id, role_id=role_to_assign.id))
```

## Test Coverage Summary

| Module | Coverage | Change |
|--------|----------|--------|
| `app/routers/auth.py` | 100% | +59% |
| `app/routers/me.py` | 96% | +56% |
| `app/models.py` | 100% | - |
| `app/schemas.py` | 100% | - |
| `app/security.py` | 100% | +43% |
| `app/main.py` | 92% | +19% |
| **Overall** | **70.92%** | +8% |

## Verification

Tested the complete registration flow:
1. ✅ Fresh database with migrations applied
2. ✅ First user registration → assigned admin role
3. ✅ Second user registration → assigned technician role
4. ✅ Login and JWT token generation working
5. ✅ /me endpoint returns user info with roles
6. ✅ All 14 tests passing
7. ✅ Registration fails gracefully when roles aren't seeded
