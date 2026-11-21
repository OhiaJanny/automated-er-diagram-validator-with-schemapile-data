from __future__ import annotations

import argparse
import hashlib
import os
import urllib.request
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]

RAW_DIR = (
    PROJECT_ROOT
    / "data"
    / "raw"
)

RAW_PATH = (
    RAW_DIR
    / "schemapile-perm.json.gz"
)

DOWNLOAD_URL = (
    "https://zenodo.org/records/12682521/"
    "files/schemapile-perm.json.gz"
)

EXPECTED_MD5 = (
    "1b0e9fe456e31a9c6dd5d9d1cfe56890"
)

CHUNK_SIZE = 1024 * 1024


def compute_md5(
    path: Path,
) -> str:
    digest = hashlib.md5()

    with path.open("rb") as file:
        while True:
            chunk = file.read(CHUNK_SIZE)

            if not chunk:
                break

            digest.update(chunk)

    return digest.hexdigest()


def verify_download(
    path: Path,
) -> bool:
    if not path.exists():
        return False

    actual_md5 = compute_md5(path)

    return (
        actual_md5.lower()
        == EXPECTED_MD5.lower()
    )


def download_schemapile(
    force: bool = False,
) -> Path:
    RAW_DIR.mkdir(
        parents=True,
        exist_ok=True,
    )

    if RAW_PATH.exists():

        if verify_download(
            RAW_PATH
        ):
            if not force:
                print(
                    "SchemaPile-Perm is already "
                    "downloaded and its checksum "
                    "is valid."
                )

                return RAW_PATH

        elif not force:
            raise ValueError(
                "Existing SchemaPile file has "
                "an unexpected checksum. "
                "Run again with --force to "
                "replace it."
            )

    temporary_path = (
        RAW_PATH.with_suffix(
            ".json.gz.part"
        )
    )

    if temporary_path.exists():
        temporary_path.unlink()

    print(
        "Downloading SchemaPile-Perm..."
    )

    print(
        DOWNLOAD_URL
    )

    request = urllib.request.Request(
        DOWNLOAD_URL,
        headers={
            "User-Agent": (
                "ER-Validation-Research/"
                "1.0"
            )
        },
    )

    downloaded_bytes = 0

    try:
        with urllib.request.urlopen(
            request
        ) as response:

            content_length = (
                response.headers.get(
                    "Content-Length"
                )
            )

            total_bytes = (
                int(content_length)
                if content_length
                else None
            )

            with temporary_path.open(
                "wb"
            ) as output:

                while True:
                    chunk = response.read(
                        CHUNK_SIZE
                    )

                    if not chunk:
                        break

                    output.write(chunk)

                    downloaded_bytes += (
                        len(chunk)
                    )

                    if total_bytes:
                        percent = (
                            downloaded_bytes
                            / total_bytes
                            * 100
                        )

                        print(
                            f"\rDownloaded "
                            f"{percent:6.2f}%",
                            end="",
                        )

        print()

        os.replace(
            temporary_path,
            RAW_PATH,
        )

    except Exception:
        if temporary_path.exists():
            temporary_path.unlink()

        raise

    actual_md5 = compute_md5(
        RAW_PATH
    )

    if (
        actual_md5.lower()
        != EXPECTED_MD5.lower()
    ):
        RAW_PATH.unlink(
            missing_ok=True
        )

        raise ValueError(
            "Downloaded file checksum "
            "does not match the published "
            "SchemaPile-Perm v0.2 file.\n"
            f"Expected: {EXPECTED_MD5}\n"
            f"Observed: {actual_md5}"
        )

    print(
        "Download complete."
    )

    print(
        f"Saved to: {RAW_PATH}"
    )

    print(
        "MD5 checksum verified."
    )

    return RAW_PATH


def main() -> None:
    parser = argparse.ArgumentParser(
        description=(
            "Download the published "
            "SchemaPile-Perm dataset."
        )
    )

    parser.add_argument(
        "--force",
        action="store_true",
        help=(
            "Redownload even if the "
            "dataset already exists."
        ),
    )

    args = parser.parse_args()

    download_schemapile(
        force=args.force
    )


if __name__ == "__main__":
    main()