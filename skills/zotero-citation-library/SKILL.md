---
name: zotero-citation-library
description: "How to call ZoteroAgent's tools to read a Zotero library."
---

# Calling ZoteroAgent

This skill says how to call the ZoteroAgent extension's tools. For the method itself, use the BAAM skill `citation-library-management`.

## Tools

- `zotero_status`: shows which targets are configured, their routes and which settings are present. It never shows a value and makes no network call.
- `zotero_get`: reads from a target. It sends `GET`, or `POST` on routes declared as reads, and is marked read only, so Biorouter's Smart approval runs it without asking.
- `zotero_write`: changes data on a declared write route. It is marked destructive, so Biorouter asks you before every call.

## Targets

| Target | Base URL | Credential | Reads | Writes |
| --- | --- | --- | --- | --- |
| `zotero` | `https://api.zotero.org` | `ZOTERO_API_KEY` (header, optional) | GET `/**` | POST `/users/*/items`, POST `/users/*/collections`, POST `/groups/*/items`, POST `/groups/*/collections` |

## Rules

- Call `zotero_status` first. It shows which targets are configured and which
  settings are missing, without showing any value.
- Pass `path` relative to the target's base URL, for example `/users/ID/items`. Put
  query values in `query`, not in the path.
- A full URL is accepted only on the target's own host. The extension refuses any
  other host, so do not try to reach other services through it.
- Never put a credential in a tool argument. The extension attaches it.
- `zotero_write` changes data. Use it only for what the person asked for; Biorouter asks them to approve every call.
