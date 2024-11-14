import datetime
import json

import pytz
import requests_cache

BASE_URL = "https://pypi.org/simple"
# Provenance began to be persisted on 2024-10-03
# And `pypa/gh-action-pypi-publish` turned it automatically on 2024-10-29
ATTESTATION_ENABLEMENT = datetime.datetime(2024, 10, 29, tzinfo=datetime.timezone.utc)

DEPRECATED_PACKAGES = {
    "BeautifulSoup",
    "bs4",
    "distribute",
    "django-social-auth",
    "nose",
    "pep8",
    "pycrypto",
    "pypular",
    "sklearn",
}

# Keep responses for one hour
SESSION = requests_cache.CachedSession("requests-cache", expire_after=60 * 60)


def get_json_url(package_name):
    return BASE_URL + "/" + package_name + "/"


def annotate_wheels(packages):
    print("Getting wheel data...")
    num_packages = len(packages)
    for index, package in enumerate(packages):
        print(index + 1, num_packages, package["name"])
        has_provenance = False
        latest_upload = None
        url = get_json_url(package["name"])
        response = SESSION.get(
            url, headers={"Accept": "application/vnd.pypi.simple.v1+json"}
        )
        if response.status_code != 200:
            print(" ! Skipping " + package["name"])
            continue
        data = response.json()

        for file in data["files"]:
            if file.get("provenance", None):
                has_provenance = True

            upload_time = datetime.datetime.fromisoformat(file["upload-time"])
            if not latest_upload or upload_time > latest_upload:
                latest_upload = upload_time

        package["wheel"] = has_provenance

        # Display logic. I know, I'm sorry.
        package["value"] = 1
        if has_provenance:
            package["css_class"] = "success"
            package["icon"] = "🔏"
            package["title"] = "This package provides attestations."
        elif latest_upload < ATTESTATION_ENABLEMENT:
            package["css_class"] = "default"
            package["icon"] = "⏰"
            package["title"] = (
                "This package was last uploaded before PEP 740 was enabled."
            )
        else:
            package["css_class"] = "warning"
            package["icon"] = ""
            package["title"] = "This package doesn't provide attestations (yet!)"


def get_top_packages():
    print("Getting packages...")

    with open("top-pypi-packages.json") as data_file:
        packages = json.load(data_file)["rows"]

    # Rename keys
    for package in packages:
        package["downloads"] = package.pop("download_count")
        package["name"] = package.pop("project")

    return packages


def not_deprecated(package):
    return package["name"] not in DEPRECATED_PACKAGES


def remove_irrelevant_packages(packages, limit):
    print("Removing cruft...")
    active_packages = list(filter(not_deprecated, packages))
    return active_packages[:limit]


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
