"""Test helpers."""


def registration_payload(
    email: str,
    *,
    password: str = "StrongPass!123",
    requested_role: str = "technician",
    full_name: str = "Test User",
    phone_number: str = "+1-555-0000",
    address: str = "123 Main St",
) -> dict:
    """Return a payload for /auth/register with sensible defaults."""
    return {
        "email": email,
        "password": password,
        "full_name": full_name,
        "phone_number": phone_number,
        "address": address,
        "requested_role": requested_role,
    }
