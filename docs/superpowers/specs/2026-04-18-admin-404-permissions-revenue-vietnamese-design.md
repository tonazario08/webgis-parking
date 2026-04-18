# Design Spec: 404 pages, manager permissions UI, manager-only revenue, full Vietnamese text normalization

Date: 2026-04-18
Project: webgis_parking
Status: Approved in conversation

## 1) Objective and scope

Implement the following product changes with minimal architectural disruption:

1. Add missing 404 pages, split by context:
   - Public-facing 404 page
   - Manager-facing 404 page
2. Add permission management in admin area:
   - Keep Django admin (`/dj-admin/`) for full User/Group/Permission management
   - Add a dedicated permission screen in custom manager UI (`/manager/`) for fast user-group assignment
3. Move revenue section fully out of public surface and into manager/admin surface only
4. Fix Vietnamese copy quality across the entire UI (add proper diacritics and unify wording)
5. Keep existing Django forgot-password behavior (email reset link), but normalize UI/text in related pages

Out of scope:
- Replacing Django auth/reset mechanics
- Introducing full i18n framework refactor
- Unrelated UI redesigns

## 2) Constraints and decisions

Confirmed decisions from user:
- Vietnamese text normalization applies to entire interface (public + manager + email templates)
- Permission feature must exist in both places: Django admin and custom manager
- Revenue must be removed from public routes/UI and available only in manager/admin
- 404 must be separated into two visual variants (public and manager)
- Forgot password keeps current Django flow; only UI/copy updates

Implementation strategy chosen:
- Keep current architecture and patch at integration points (fast, low-risk, in-scope)

## 3) Architecture changes

### 3.1 404 handling with dual templates

Current state:
- No dedicated split 404 experience.

Design:
- Configure centralized 404 handler in Django root URL config.
- Handler decides template by request path:
  - `/manager/...` -> manager-style 404 template
  - other paths -> public-style 404 template
- Ensure HTTP status remains 404.

Target components:
- `webgis_parking/urls.py`: register `handler404`
- `parking/views.py` (or dedicated lightweight module): custom 404 view function
- Templates:
  - `parking/templates/404.html` (public)
  - `parking/templates/parking/manager/404.html` (manager)

### 3.2 Permission management in manager UI

Current state:
- Django admin exists (`/dj-admin/`) and can manage permissions.
- Custom manager UI currently lacks dedicated permission page.

Design:
- Keep `/dj-admin/` unchanged for full admin-level control.
- Add manager page `manager/permissions/` for quick assignment of groups to users.
- Only full manager (`is_staff` or `is_superuser`) can access.
- Limited manager group (`parking_user_creator`) cannot access.

Data model usage:
- Reuse Django auth models (`User`, `Group`, `Permission`) without schema changes.

Behavior:
- List users (search optional)
- Show each user’s current groups
- Submit selected groups to update `user.groups.set(...)`
- Write activity log entry for audit visibility

Target components:
- `parking/manager_urls.py`: new routes for permissions page/update action
- `parking/manager_views.py`: permission list/update view(s)
- `parking/templates/parking/manager/permissions.html`: manager permission UI
- `parking/templates/parking/manager/base.html`: add sidebar entry for full managers

### 3.3 Revenue moved to manager-only surface

Current state:
- Revenue route exists in public URL config.

Design:
- Remove public revenue route and navigation entry.
- Expose revenue page under manager routes only.
- Restrict to full manager permission.
- Reuse existing revenue calculation logic; no business logic expansion.

Target components:
- `parking/urls.py`: remove public `revenue/` endpoint
- `parking/views.py`: remove or retire public revenue view mapping
- `parking/manager_urls.py`: add manager revenue route
- `parking/manager_views.py`: manager revenue view (reusing current computation)
- `parking/templates/parking/manager/base.html`: add manager menu link
- `parking/templates/parking/revenue.html`: either migrate to manager namespace or replace with manager-specific template

### 3.4 Vietnamese copy normalization across UI

Current state:
- Large portion of templates/messages are Vietnamese without diacritics and inconsistent wording.

Design:
- Normalize text across:
  - Public templates
  - Manager templates
  - Auth/reset templates
  - Email templates (HTML + TXT)
  - User-facing flash messages in views/forms where practical
- Keep message meaning unchanged; change is linguistic consistency and readability.

Rules:
- Prefer correct Vietnamese with dấu.
- Keep domain terms consistent (e.g., “bãi đỗ”, “đăng ký”, “đăng nhập”, “mật khẩu”, “không”).
- Avoid changing variable names or identifiers unless required.

Primary components:
- `parking/templates/parking/**/*.html`
- `parking/templates/parking/**/*.txt`
- `parking/templates/parking/manager/**/*.html`
- selective strings in `parking/views.py`, `parking/manager_views.py`, `parking/forms.py`, `parking/utils/*.py`

### 3.5 Forgot-password flow

Current state:
- Django PasswordReset views are wired and functional.

Design:
- Keep route/view behavior intact.
- Update UI text and tone in reset templates and email templates only.
- Ensure links and success/failure states stay unchanged functionally.

Target components:
- `parking/templates/parking/auth/password_reset_form.html`
- `parking/templates/parking/auth/password_reset_done.html`
- `parking/templates/parking/auth/password_reset_confirm.html`
- `parking/templates/parking/auth/password_reset_complete.html`
- password-reset email subject/body templates

## 4) Security and authorization considerations

- Manager permission management endpoints must enforce full-manager checks on both GET and POST.
- Never allow limited manager to escalate privileges.
- Use POST + CSRF for permission updates.
- Revenue data must not remain publicly reachable from old route.

## 5) Error handling behavior

- Public and manager 404 return distinct templates, same status code (404).
- Permission update failures show actionable message and do not partially apply changes.
- Missing/invalid user/group references return safe message and redirect back to permission page.

## 6) Testing strategy

### Automated tests (minimum additions)
- Route protection tests:
  - manager permission page inaccessible to anonymous users
  - manager permission page inaccessible to limited manager
  - manager permission page accessible to full manager
- Revenue surface tests:
  - old public revenue URL is absent/not reachable
  - manager revenue URL requires manager auth
- 404 tests:
  - unknown public URL renders public 404 template
  - unknown manager URL renders manager 404 template

### Manual verification
- Navigate unknown URL from public and manager contexts to verify visual split
- Update user groups in manager permission page and confirm effect in `/dj-admin/`
- Confirm revenue appears in manager sidebar and not in public navigation
- Run full forgot-password flow (request, email link, reset, completion)
- Spot-check key pages for corrected Vietnamese with dấu

## 7) Rollout and compatibility

- No DB migration expected for this scope.
- Changes are backward-compatible at data level.
- Public URL removal for revenue is intentional product behavior change.

## 8) File-level change map

Likely touched files:
- `webgis_parking/urls.py`
- `parking/urls.py`
- `parking/manager_urls.py`
- `parking/views.py`
- `parking/manager_views.py`
- `parking/forms.py` (text normalization only if needed)
- `parking/templates/404.html` (new)
- `parking/templates/parking/manager/404.html` (new)
- `parking/templates/parking/manager/base.html`
- `parking/templates/parking/manager/permissions.html` (new)
- `parking/templates/parking/revenue.html` or manager-specific replacement
- Auth and email templates under `parking/templates/parking/auth/` and `parking/templates/parking/email/`

## 9) Success criteria

1. Public and manager 404 pages are visually distinct and return status 404.
2. Permission assignment can be done in manager UI by full managers only.
3. Django admin permission management remains operational at `/dj-admin/`.
4. Revenue is no longer available on public surface and is available in manager surface.
5. Forgot-password flow behavior is unchanged, with improved Vietnamese UI/copy.
6. Vietnamese text across UI is normalized with diacritics and consistent wording.
