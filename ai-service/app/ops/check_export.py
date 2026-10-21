"""The export bundle, against the real schema.

``python -m app.ops.check_export [user-id]`` builds the portable export for
one user against the database this deployment actually has, and says
whether it worked.

It exists because the export's queries are the one part of the bundle
that no offline test can reach: the fetch functions are monkeypatched in
the unit tests, so a column the schema does not have -- or a UUID the
canonical serializer does not know -- is invisible there. Both of those
were true at once, and both shipped, and the only thing that found them
was the end-to-end suite against a real database.

This is the cheap version of that check: it needs the database and
nothing else. No backend, no frontend, no app images -- so it can run in
the nightly job, where the app images are deliberately not built.

It builds the bundle for whichever user is named, and a bundle for a
user with no rows is still a bundle: the queries run, the serializer
runs, and the hash is computed over what came back. That is exactly the
path that was broken.

Exit codes: ``0`` the bundle was built and hashed; ``1`` it was not, and
the reason is on stderr.
"""

from __future__ import annotations

import asyncio
import json
import sys

from app.core import db
from app.features import export as ex


async def _check(user_id: str) -> int:
    try:
        bundle = await ex.export_bundle(user_id)
    except Exception as err:  # the point of the check is to report this
        print(f"the export did not build for {user_id}: {err}", file=sys.stderr)
        return 1

    manifest = bundle.get("manifest") or {}
    content_hash = manifest.get("content_hash") or ""
    if len(content_hash) != 64:
        print(
            f"the export built but its content hash is {content_hash!r}, which is "
            "not a sha256",
            file=sys.stderr,
        )
        return 1

    # The hash has to be over the data, and the data has to survive the
    # round trip the bundle promises: the canonical form is what the hash
    # is computed over, and the bundle is what ships.
    canonical = ex.canonical_json(bundle["data"])
    if not canonical:
        print("the export built but its data is empty", file=sys.stderr)
        return 1
    if json.loads(canonical) != json.loads(json.dumps(bundle["data"], default=str)):
        print(
            "the bundle's data does not survive the canonical form it is hashed over",
            file=sys.stderr,
        )
        return 1

    print(
        json.dumps(
            {
                "user_id": user_id,
                "schema_version": bundle.get("schema_version"),
                "content_hash": content_hash,
                "counts": manifest.get("counts"),
            },
            ensure_ascii=False,
        )
    )
    return 0


async def main(argv: list[str]) -> int:
    user_id = argv[1] if len(argv) > 1 else "00000000-0000-0000-0000-000000000000"
    try:
        await db.init_db()
        return await _check(user_id)
    finally:
        await db.close_db()


if __name__ == "__main__":
    raise SystemExit(asyncio.run(main(sys.argv)))
