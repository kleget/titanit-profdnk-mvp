from __future__ import annotations

import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT_DIR / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))


def main() -> int:
    from app.config import settings
    from app.db import Base, SessionLocal, engine
    from app.services.seed import (
        DEMO_ADMIN_EMAIL,
        DEMO_ADMIN_PASSWORD,
        DEMO_PSYCHOLOGIST_EMAIL,
        DEMO_PSYCHOLOGIST_PASSWORD,
        ensure_demo_showcase_data,
        seed_initial_data,
    )

    print("[demo-reset] dropping schema...")
    Base.metadata.drop_all(bind=engine)
    print("[demo-reset] creating schema...")
    Base.metadata.create_all(bind=engine)

    with SessionLocal() as db:
        print("[demo-reset] seeding baseline data...")
        seed_initial_data(db)
        print("[demo-reset] preparing showcase submissions...")
        summary = ensure_demo_showcase_data(db, target_submissions=3)

    base_url = settings.base_url.rstrip("/")
    print("\n=== Demo reset completed ===")
    print(f"Admin:        {DEMO_ADMIN_EMAIL} / {DEMO_ADMIN_PASSWORD}")
    print(f"Psychologist: {DEMO_PSYCHOLOGIST_EMAIL} / {DEMO_PSYCHOLOGIST_PASSWORD}")
    print(f"Features:     {base_url}/features")
    print(f"Demo test:    {base_url}/tests/{summary['test_id']}")
    print(f"Client link:  {base_url}/t/{summary['share_token']}")
    print(
        "Prepared: "
        f"submissions={summary['submissions_count']}, "
        f"named_links={summary['named_links_count']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
