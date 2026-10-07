# Current API and authentication routes

Current milestone provides session authentication and a read-only current-user API.
Other assignment APIs are pending. DRF defaults require authenticated sessions and
paginate future list resources with a page size of 25.

| Route | Method | Behaviour |
| --- | --- | --- |
| /login/ | GET, POST | HTML form; CSRF-protected Django session login |
| /logout/ | POST | CSRF-protected session logout; redirect to login |
| /password/change/ | GET, POST | HTML form; old password + new password/confirmation |
| / | GET | Authenticated foundation landing page |
| /api/auth/me/ | GET | Current account identity only |

`/api/auth/me/` example:

```json
{"id": 4, "username": "asha@demo.local", "name": "Asha Deshmukh", "role": "EMPLOYEE", "role_label": "Employee"}
```

- No session, inactive account or initial password pending: API returns 403.
- Authenticated, initial password changed: current-user GET returns 200, with no-store caching.
- Mutations to current-user endpoint: 405 for an authenticated user (or 403 if CSRF
  validation rejects a state-changing request first). No writable role/identity fields.
- Anonymous HTML pages redirect to login with a local `next` destination. External
  destinations are rejected. Login failures return the same generic HTML error (200),
  retain the login identifier and clear the password.
- Missing/invalid CSRF on login, password change or logout: 403. GET logout: 405
  for an authenticated account. Successful login/password change/logout redirect (302).
- Password validation failure: HTML form (200) with field errors; password remains
  unchanged. Initial-password lock persists. Successful change clears that lock and
  invalidates other sessions; current session remains signed in.

Use the shared login page to obtain a session and CSRF cookie. Send cookies on
same-origin requests; future API mutations will require `X-CSRFToken`. BasicAuth,
JWT and public signup are not configured. Backend project/object permissions are
part of the next implementation milestone, not provided by role-aware navigation.
