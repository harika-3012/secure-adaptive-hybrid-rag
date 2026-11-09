"""Creates backend/.env from the example and fills in a random JWT_SECRET if it is empty."""
from __future__ import annotations

import secrets
import shutil
from pathlib import Path

BACKEND = Path(__file__).resolve().parents[1] / "backend"


def main() -> None:
    env_path = BACKEND / ".env"
    if not env_path.exists():
        shutil.copy(BACKEND / ".env.example", env_path)
    lines = env_path.read_text(encoding="utf-8").splitlines()
    updated = []
    for line in lines:
        if line.startswith("JWT_SECRET=") and line.strip() == "JWT_SECRET=":
            line = f"JWT_SECRET={secrets.token_urlsafe(48)}"
        updated.append(line)
    env_path.write_text("\n".join(updated) + "\n", encoding="utf-8")
    print(f"Environment ready: {env_path}")


if __name__ == "__main__":
    main()
