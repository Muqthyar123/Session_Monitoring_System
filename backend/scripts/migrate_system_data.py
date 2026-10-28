"""Legacy JSON database migration was retired when MongoDB became authoritative."""


def main() -> None:
    raise SystemExit(
        "This legacy db_store.json migration is disabled. "
        "It will not modify local files or MongoDB. Use an explicit, reviewed MongoDB migration instead."
    )


if __name__ == "__main__":
    main()
