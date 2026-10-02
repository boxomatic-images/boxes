#!/usr/bin/env python3

import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path
from urllib.request import Request, urlopen


OWNER = "boxomatic-images"
REPO = "boxes"

API_URL = f"https://api.github.com/repos/{OWNER}/{REPO}/releases"

CATALOG_FILE = Path(".github/scripts/catalog.json")
OUTPUT_DIR = Path("docs")

RELEASE_RE = re.compile(
    r"^(?P<box>.+)-(?P<architecture>[^-]+)-"
    r"(?P<provider>[^-]+)-v(?P<version>\d+\.\d+\.\d+)$"
)


def github_get(url):
    """
    Fetch JSON from the GitHub API.
    """

    headers = {
        "Accept": "application/vnd.github+json",
        "X-GitHub-Api-Version": "2026-03-10",
        "User-Agent": "boxomatic-catalog-generator",
    }

    token = os.environ.get("GITHUB_TOKEN")

    if token:
        headers["Authorization"] = f"Bearer {token}"

    request = Request(url, headers=headers)

    with urlopen(request) as response:
        return json.load(response)


def load_image_metadata():
    """
    Load descriptions from images.json.

    Expected format:

    {
        "alpine-3.24": {
            "description": "Alpine 3.24"
        }
    }
    """

    if not CATALOG_FILE.exists():
        print(
            f"WARNING: {CATALOG_FILE} not found",
            file=sys.stderr,
        )

        return {}

    try:
        with CATALOG_FILE.open("r", encoding="utf-8") as f:
            data = json.load(f)

    except json.JSONDecodeError as exc:
        print(
            f"ERROR: invalid JSON in {CATALOG_FILE}: {exc}",
            file=sys.stderr,
        )
        sys.exit(1)

    if not isinstance(data, dict):
        print(
            f"ERROR: {CATALOG_FILE} must contain a JSON object",
            file=sys.stderr,
        )
        sys.exit(1)

    return data


def get_all_releases():
    """
    Retrieve all releases from the GitHub repository.
    """

    releases = []
    page = 1

    while True:
        url = f"{API_URL}?per_page=100&page={page}"

        print(f"Fetching releases page {page}...")

        batch = github_get(url)

        if not batch:
            break

        releases.extend(batch)

        page += 1

    return releases


def parse_release(tag):
    """
    Parse a release tag.

    Example:

        alpine-3.24-amd64-virtualbox-v20260930.0.1

    Returns:

        box
        architecture
        provider
        version
    """

    match = RELEASE_RE.match(tag)

    if not match:
        return None

    return {
        "box": match.group("box"),
        "architecture": match.group("architecture"),
        "provider": match.group("provider"),
        "version": match.group("version"),
    }


def find_box_asset(release):
    """
    Find the .box asset in a GitHub Release.

    The expected release contains exactly one .box file.
    """

    box_assets = [
        asset
        for asset in release.get("assets", [])
        if asset.get("name", "").endswith(".box")
    ]

    if not box_assets:
        return None

    if len(box_assets) > 1:
        print(
            f"WARNING: release {release['tag_name']} "
            f"contains multiple .box assets; using {box_assets[0]['name']}",
            file=sys.stderr,
        )

    return box_assets[0]


def get_checksum(asset):
    """
    Get SHA-256 checksum from GitHub asset digest.

    GitHub returns:

        sha256:abcdef...

    Vagrant expects:

        abcdef...
    """

    digest = asset.get("digest")

    if not digest:
        return None

    if digest.startswith("sha256:"):
        digest = digest[len("sha256:"):]

    return digest


def version_sort_key(version):
    """
    Convert semantic version string into a tuple.

    Example:

        20260930.0.1 -> (20260930, 0, 1)
    """

    return tuple(int(value) for value in version.split("."))


def generate_catalog(releases, image_metadata):
    """
    Generate catalog data grouped by box name.
    """

    catalogs = defaultdict(lambda: defaultdict(list))

    for release in releases:

        # Ignore drafts.
        if release.get("draft"):
            continue

        # Ignore prereleases.
        if release.get("prerelease"):
            continue

        tag = release.get("tag_name", "")

        parsed = parse_release(tag)

        if not parsed:
            print(
                f"WARNING: ignoring release with unexpected name: {tag}",
                file=sys.stderr,
            )
            continue

        box_name = parsed["box"]
        architecture = parsed["architecture"]
        provider = parsed["provider"]
        version = parsed["version"]

        asset = find_box_asset(release)

        if not asset:
            print(
                f"WARNING: release has no .box asset: {tag}",
                file=sys.stderr,
            )
            continue

        checksum = get_checksum(asset)

        if not checksum:
            print(
                f"WARNING: .box asset has no SHA-256 digest: {tag}",
                file=sys.stderr,
            )
            continue

        provider_data = {
            "name": provider,
            "url": asset["browser_download_url"],
            "checksum_type": "sha256",
            "checksum": checksum,
            "architecture": architecture,
            "default_architecture": architecture == "amd64",
        }

        catalogs[box_name][version].append(provider_data)

    return catalogs


def write_catalogs(catalogs, image_metadata):
    """
    Write catalog/*.json files.
    """

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for box_name, versions in sorted(catalogs.items()):

        metadata = image_metadata.get(box_name)

        if metadata is None:
            print(
                f"WARNING: no metadata found in images.json "
                f"for image: {box_name}",
                file=sys.stderr,
            )
            description = box_name

        else:
            description = metadata.get("description")

            if not description:
                print(
                    f"WARNING: no description found in images.json "
                    f"for image: {box_name}",
                    file=sys.stderr,
                )
                description = box_name

        version_list = []

        for version, providers in versions.items():

            # Remove duplicate providers/architectures.
            unique_providers = {}

            for provider in providers:
                key = (
                    provider["name"],
                    provider["architecture"],
                )

                unique_providers[key] = provider

            provider_list = list(unique_providers.values())

            # Keep provider order stable.
            provider_list.sort(
                key=lambda item: (
                    item["name"],
                    item["architecture"],
                )
            )

            version_list.append(
                {
                    "version": version,
                    "providers": provider_list,
                }
            )

        # Newest version first.
        version_list.sort(
            key=lambda item: version_sort_key(item["version"]),
            reverse=True,
        )

        catalog = {
            "name": f"boxomatic/{box_name}",
            "description": description,
            "versions": version_list,
        }

        output_file = OUTPUT_DIR / f"{box_name}.json"

        with output_file.open("w", encoding="utf-8") as f:
            json.dump(
                catalog,
                f,
                indent=2,
                ensure_ascii=False,
            )
            f.write("\n")

        print(f"Generated {output_file}")


def generate_index(image_names, image_metadata, output_dir):
    index_file = output_dir / "index.html"

    rows = []

    for image_name in sorted(image_names):
        description = image_metadata.get(image_name, {}).get("description")

        if not description:
            print(
                f"Warning: no description found for image '{image_name}'"
            )
            description = image_name

        rows.append(
            f'        <li>{description}: <a href="{image_name}.json">'
            f'boxomatic/{image_name}</a></li>'
        )

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Boxomatic Images</title>
    <style>
        body {{
            font-family: sans-serif;
            max-width: 900px;
            margin: 40px auto;
            padding: 0 20px;
        }}

        li {{
            margin: 8px 0;
        }}

        a {{
            text-decoration: none;
        }}

        a:hover {{
            text-decoration: underline;
        }}
    </style>
</head>
<body>
    <h1>Boxomatic Images</h1>

    <p>
        Vagrant box metadata catalogs generated from
        <a href="https://github.com/boxomatic-images/boxes/releases">
        GitHub Releases</a>.
    </p>

    <ul>
{chr(10).join(rows)}
    </ul>
</body>
</html>
"""

    index_file.write_text(html, encoding="utf-8")


def main():
    print("Loading image metadata...")

    image_metadata = load_image_metadata()

    print("Fetching GitHub Releases...")

    releases = get_all_releases()

    print(f"Found {len(releases)} releases.")

    print("Generating catalogs...")

    catalogs = generate_catalog(
        releases,
        image_metadata,
    )

    print(f"Found {len(catalogs)} box images.")

    write_catalogs(
        catalogs,
        image_metadata,
    )

    generate_index(catalogs, image_metadata, OUTPUT_DIR)

    print("Catalog generation complete.")


if __name__ == "__main__":
    main()
