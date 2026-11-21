# ZoteroAgent

Read Zotero libraries, collections, items and tags through the Zotero web API, and add items or collections with approval. Your key goes only to api.zotero.org.

Current version: **0.2.0**

This is a Biorouter extension (a `.brxt` bundle) built on the BRXT adapter kit
1.0.0. Install it from BAAM in Biorouter, or from a file:

```bash
biorouter extension install dist/zoteroagent.brxt
```

## Tools

- `zotero_status`: shows which targets are configured, their routes and which settings are present. It never shows a value and makes no network call.
- `zotero_get`: reads from a target. It sends `GET`, or `POST` on routes declared as reads, and is marked read only, so Biorouter's Smart approval runs it without asking.
- `zotero_write`: changes data on a declared write route. It is marked destructive, so Biorouter asks you before every call.

## Targets

| Target | Base URL | Credential | Reads | Writes |
| --- | --- | --- | --- | --- |
| `zotero` | `https://api.zotero.org` | `ZOTERO_API_KEY` (header, optional) | GET `/**` | POST `/users/*/items`, POST `/users/*/collections`, POST `/groups/*/items`, POST `/groups/*/collections` |

## Settings

| Variable | Required | Secret | Purpose |
| --- | --- | --- | --- |
| `ZOTERO_API_KEY` | no | yes | Zotero API key, sent only to api.zotero.org |
| `ZOTERO_USER_ID` | no | no | Your numeric Zotero user id, used in paths like /users/<id>/items |
| `ZOTERO_GROUP_ID` | no | no | A numeric Zotero group id, used in paths like /groups/<id>/items |
| `ZOTERO_LOG_LEVEL` | no | no | Logging level |

## How it protects your credentials

- Each credential is attached only to requests for its own target's host. A full URL
  that names another host, a path starting with `//`, plain `http` and a redirect to
  another host are all refused, so a prompt that names a URL cannot move a key off
  the service it belongs to.
- Reads use `GET`, or `POST` on the routes declared as reads. Writes go through a
  separate tool that Biorouter asks you to approve every time, and only to declared
  routes.
- The extension never runs a local command. Use Biorouter's Developer shell for that.
- Credential values never appear in tool results, error messages or logs.

## Develop and release

```bash
uv sync
uv run python -m unittest discover -s tests -v   # contract tests and leak suite
uv run python scripts/build_brxt.py               # writes dist/zoteroagent.brxt and SHA256SUMS
uv run python scripts/version.py X.Y.Z            # moves every version string together
```

Push a tag `vX.Y.Z` equal to the manifest version to publish a release. The release
workflow refuses any other tag. Do not edit `src/zoteroagent/_kit/` or `tests/kit_testing/`:
they are vendored from the kit in the Biorouter repository
(`scripts/brxt-adapter-kit/`, documented in `docs/extensions/brxt-adapter-kit.md`).

## License

Apache-2.0. See `LICENSE` and `NOTICE`.
