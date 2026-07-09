# Design Spec — CI green: frontend TS error + ecdsa CVE

**Date:** 2026-07-09
**Context:** Two pre-existing CI failures on `main` (surfaced while merging #28),
unrelated to #28. This change turns both red checks green.

## Goal

Fix the two failing CI checks on `main`:
1. **Frontend — lint, tipos y build**: `tsc` error `TS2493` in
   `frontend/src/views/CotizacionesEdit.test.tsx:61`.
2. **Seguridad — auditoría de dependencias**: `pip-audit` fails on
   `ecdsa 0.19.2` / `PYSEC-2026-1325`.

## Fix 1 — Frontend TS2493

**Root cause:** the hoisted mocks are declared with a zero-arg implementation:
```ts
updateSpy: vi.fn(() => Promise.resolve({ data: {} })),
```
so Vitest infers the call-args tuple as `[]`. Line 61 reads
`updateSpy.mock.calls[0][0]`, and TypeScript rejects index `0` on an empty tuple.

**Chosen approach:** give the mock implementations typed parameters so the
inferred args tuple has elements (`[number, unknown?]`), making
`.mock.calls[0][0]` type `number`. Surgical, keeps type-safety, no runtime change.

**Rejected:** casting `(updateSpy.mock.calls[0] as any[])[0]` — loses type-safety
and hides the real fix; `@ts-expect-error` — silences instead of fixing.

## Fix 2 — ecdsa PYSEC-2026-1325

**Root cause:** `ecdsa 0.19.2` is a transitive dependency of
`python-jose[cryptography]==3.5.0`. The advisory is a timing side-channel in
**ECDSA signing**. `ecdsa 0.19.2` is the latest release — **no fixed version
exists**.

**Reachability analysis:** the app signs JWTs with **HS256** (HMAC-SHA256,
`config.py ALGORITHM="HS256"`, symmetric `SECRET_KEY`). `python-jose` only imports
`ecdsa` for `ES*` (elliptic-curve) algorithms, and with the `[cryptography]` extra
EC operations use the `cryptography` backend anyway. The `ecdsa` package is
therefore **never imported at runtime** → the vulnerability is unreachable.

**Chosen approach:** ignore this specific advisory in the `pip-audit` CI step with
an inline justification comment (`--ignore-vuln PYSEC-2026-1325`). Proportionate:
no fix exists and the code path is unreachable. Add a PENDIENTES note to revisit
dropping `python-jose` for `PyJWT` (which has no `ecdsa` dependency) if we ever
want to remove the package entirely.

**Rejected:** migrating `python-jose` → `PyJWT` now — touches the auth-critical
token create/decode path (`security.py`), a large blast radius for an unreachable
transitive vuln; keep as documented future debt, not this change. Bumping `ecdsa`
— impossible, no fixed release.

## Threat model

Fix 2 touches a security gate. Suppressing a CVE is only safe because the code
path is proven unreachable (HS256 only, cryptography backend, ecdsa never
imported). The ignore is scoped to the single advisory ID, so any *new* advisory
still fails the audit. Documented in the workflow comment and PENDIENTES so the
suppression is auditable, not silent.

## Scope

2 tasks: frontend test mock typing; ci.yml pip-audit ignore + PENDIENTES note.
No app runtime code changes.
