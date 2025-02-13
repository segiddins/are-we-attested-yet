import csv
import datetime
import json

import pytz
import requests_cache

BASE_URL = "https://rubygems.org"
# And `rubygems/release-gem` turned it automatically on 2024-11-20
ATTESTATION_ENABLEMENT = datetime.datetime(2024, 11, 20)

PUBLISHER_URLS = (
    "https://github.com",
    "http://github.com",
    # "http://gitlab.com",
    # "https://gitlab.com",
)

DEPRECATED_PACKAGES = {}

# Keep responses for one hour
SESSION = requests_cache.CachedSession("requests-cache", expire_after=60 * 60)


def get_simple_url(package_name):
    return f"{BASE_URL}/api/v1/gems/{package_name}.json"


def annotate_wheels(packages):
    print("Getting gem data...")
    num_packages = len(packages)
    for index, package in enumerate(packages):
        print(index + 1, num_packages, package["name"])
        has_provenance = package["has_attestation"]
        latest_upload = datetime.datetime.fromisoformat(package["latest_release"])
        from_supported_publisher = False
        url = get_simple_url(package["name"])
        simple_response = SESSION.get(url, headers={"Accept": "application/json"})
        if simple_response.status_code != 200:
            print(
                " ! Skipping "
                + package["name"]
                + " ({})".format(simple_response.status_code)
            )
            continue
        simple = simple_response.json()

        uris = [
            (k, v)
            for (k, v) in [
                (k, v) for (k, v) in simple["metadata"].items() if k.endswith("_uri")
            ]
            + [(k, v) for (k, v) in simple.items() if k.endswith("_uri")]
            if v
        ]
        uris = set(uris)
        for _, value in uris:
            if value.startswith(PUBLISHER_URLS):
                from_supported_publisher = True

        package["wheel"] = has_provenance

        # Display logic. I know, I'm sorry.
        package["value"] = 1
        if has_provenance:
            package["css_class"] = "success"
            package["icon"] = "🔏"
            package["title"] = "This package provides attestations."
        elif not from_supported_publisher:
            package["css_class"] = "unsupported"
            package["icon"] = ""
            package["title"] = (
                "This package is published from a source that doesn't support attestations (yet!)\nThis package was last uploaded {}\n{}".format(
                    latest_upload.strftime("%Y-%m-%d"),
                    "\n".join(sorted([f"* {k}: {v}" for (k, v) in uris])),
                )
            )
        elif latest_upload < ATTESTATION_ENABLEMENT:
            package["css_class"] = "default"
            package["icon"] = "⏰"
            package["title"] = "This package was last uploaded {}".format(
                latest_upload.strftime("%Y-%m-%d")
            )
        else:
            package["css_class"] = "warning"
            package["icon"] = ""
            package["title"] = "This package doesn't provide attestations (yet!)"

        package["title"] += "\n30 day downloads: {:,}".format(int(package["downloads"]))


def get_top_packages():
    print("Getting packages...")

    with open("sigstore_adoption.csv") as data_file:
        packages = list(csv.DictReader(data_file))

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("total_downloads")
        package["has_attestation"] = package.pop("has_attestation") == "True"

    return packages


def not_deprecated(package):
    return package["name"] not in DEPRECATED_PACKAGES


def remove_irrelevant_packages(packages, limit):
    print("Removing cruft...")
    active_packages = list(filter(not_deprecated, packages))
    if limit:
        return active_packages[:limit]
    return active_packages


def save_to_file(packages, file_name):
    now = datetime.datetime.utcnow().replace(tzinfo=pytz.utc)
    with open(file_name, "w") as f:
        f.write(
            json.dumps(
                {
                    "data": packages,
                    "last_update": now.strftime("%A, %d %B %Y, %X %Z"),
                },
                indent=1,
            )
        )
