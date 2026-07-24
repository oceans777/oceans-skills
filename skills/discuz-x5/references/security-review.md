# Discuz X5 Security Review

Use this review for plugin, template, admincp, upload, integration, and lifecycle changes.

## Authorization And Request Integrity

- Every admin action checks `IN_ADMINCP` and the relevant Discuz permission boundary.
- State-changing requests use Discuz submission and CSRF protections.
- Object identifiers are authorized against the current user or administrator, not merely validated as integers.
- Batch actions re-check every affected record.

## Input And Output

- Request data is normalized once at the module boundary.
- SQL uses table helpers or parameterized APIs.
- HTML output is escaped by default.
- Rich HTML uses an explicit allowlist and does not accept arbitrary scriptable markup.
- URLs are validated by scheme, host, and intended destination.

## Files, Uploads, And Remote Access

- Upload names are not trusted as filesystem paths.
- Extension, MIME type, decoded content, size, and storage destination are validated.
- Archive extraction blocks absolute paths, `..`, links, and oversized expansion.
- Server-side URL fetches block loopback, link-local, private, metadata-service, and rebinding targets.
- Download responses do not expose arbitrary local paths.

## Secrets And Browser Boundaries

- Provider keys, storage credentials, and upload signatures remain server-side.
- Browser code receives only scoped, expiring, or otherwise safe metadata.
- Error messages and logs do not reveal secrets, SQL, filesystem paths, or provider responses containing credentials.

## Lifecycle And Data Safety

- Install and upgrade SQL are repeatable where practical.
- Upgrade steps preserve existing rows and can resume after partial failure.
- Uninstall removes only plugin-owned data.
- Destructive migrations include backup, rollback, or explicit irreversible-change documentation.
- Metadata repair updates the owning source and stale database records without patching Discuz core rendering.

## Evidence

Record the affected entry point, trust boundary, permission check, validation method, test or reproduction command, and remaining risk. A checklist without evidence is not approval.
