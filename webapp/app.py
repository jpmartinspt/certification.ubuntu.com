# Standard library
import math

# Packages
import flask
import talisker.requests
import requests
from canonicalwebteam.flask_base.app import FlaskBase

# Local
from webapp.api import CertificationAPI
from webapp.helpers import get_download_url, get_pagination_page_array


app = FlaskBase(
    __name__,
    "certification.ubuntu.com",
    template_folder="../templates",
    static_folder="../static",
    template_404="404.html",
    template_500="500.html",
)

session = requests.Session()
talisker.requests.configure(session)
api = CertificationAPI(
    base_url="https://certification.canonical.com/api/v1", session=session
)


@app.route("/")
def index():
    return flask.render_template("index.html")


@app.route("/hardware/<canonical_id>")
def hardware(canonical_id):
    models = api.certifiedmodels(canonical_id=canonical_id)["objects"]

    if not models:
        flask.abort(404)

    model_devices = api.certifiedmodeldevices(
        canonical_id=canonical_id, limit="0"
    )["objects"]
    model_releases = api.certifiedmodeldetails(
        canonical_id=canonical_id, limit="0"
    )["objects"]

    hardware_details = {}

    for device in model_devices:
        device_info = {
            "name": (
                f"{device['make']} {device['name']}"
                f" {device['subproduct_name']}"
            ),
            "bus": device["bus"],
            "identifier": device["identifier"],
        }

        category = device["category"]
        if category not in ["BIOS", "USB"]:
            category = category.capitalize()

        if category not in hardware_details:
            hardware_details[category] = []

        hardware_details[category].append(device_info)

    release_details = {"components": {}, "releases": []}
    has_enabled_releases = False

    for model_release in model_releases:
        ubuntu_version = model_release["certified_release"]
        arch = model_release["architecture"]

        if arch == "amd64":
            arch = "64 Bit"

        release_info = {
            "name": f"Ubuntu {ubuntu_version} {arch}",
            "kernel": model_release["kernel_version"],
            "bios": model_release["bios"],
            "level": model_release["level"],
            "notes": model_release["notes"],
            "version": ubuntu_version,
            "download_url": get_download_url(models[0], model_release),
        }

        if release_info["level"] == "Enabled":
            has_enabled_releases = True

        release_details["releases"].append(release_info)

        for device_category, devices in model_release.items():
            if (
                device_category
                in ["video", "processor", "network", "wireless"]
                and devices
            ):
                device_category = device_category.capitalize()

                release_details["components"][device_category] = []

                if device_category in release_details["components"]:
                    for device in devices:
                        release_details["components"][device_category].append(
                            {
                                "name": (
                                    f"{device['make']} {device['name']}"
                                    f" {device['subproduct_name']}"
                                ),
                                "bus": device["bus"],
                                "identifier": device["identifier"],
                            }
                        )

    # Build model name
    model_names = [model["model"] for model in models]

    category = models[0]["category"]
    # default to category, which contains the least specific form_factor
    form_factor = model_release and model_release.get("form_factor", category)

    return flask.render_template(
        "hardware.html",
        canonical_id=canonical_id,
        name=", ".join(model_names),
        category=category,
        form_factor=form_factor,
        vendor=models[0]["make"],
        major_release=models[0]["major_release"],
        hardware_details=hardware_details,
        release_details=release_details,
        has_enabled_releases=has_enabled_releases,
        # Only show the first 5 components
        components=api.componentsummaries(canonical_id=canonical_id)[
            "objects"
        ][:5],
    )


@app.route("/desktop")
def desktop():
    releases = []
    vendors = []

    for release in api.certifiedreleases(limit="0")["objects"]:
        if int(release["desktops"]) > 0 or int(release["laptops"]) > 0:
            releases.append(release)

    for vendor in api.certifiedmakes(limit="0")["objects"]:
        if int(vendor["desktops"]) > 0 or int(vendor["laptops"]) > 0:
            vendors.append(vendor)

    return flask.render_template(
        "desktop/index.html", releases=releases, vendors=vendors
    )


@app.route("/desktop/models")
def desktop_models():
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    level = flask.request.args.get("level") or "Any"
    categories = flask.request.args.getlist("category") or [
        "Desktop",
        "Laptop",
    ]
    releases = flask.request.args.getlist("release")
    vendors = flask.request.args.getlist("vendors")

    if level.lower() == "any":
        level = None

    models_response = api.certifiedmodels(
        level=level,
        category__in=",".join(categories),
        major_release__in=",".join(releases) if releases else None,
        vendor=vendors,
        query=query,
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    all_releases = []
    all_vendors = []

    for release in api.certifiedreleases(limit="0")["objects"]:
        if int(release["desktops"]) > 0 or int(release["laptops"]) > 0:
            all_releases.append(release["release"])

    for vendor in api.certifiedmakes(limit="0")["objects"]:
        if int(vendor["desktops"]) > 0 or int(vendor["laptops"]) > 0:
            all_vendors.append(vendor["make"])

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "desktop/models.html",
        models=models,
        query=query,
        level=level,
        categories=categories,
        releases=releases,
        all_releases=sorted(all_releases, reverse=True),
        vendors=vendors,
        all_vendors=sorted(all_vendors),
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/server")
def server():
    vendors = api.vendorsummaries_server()["vendors"]

    releases = []

    for vendor in vendors:
        for release in vendor["releases"]:
            if release not in releases:
                releases.append(release)

    return flask.render_template(
        "server/index.html", releases=releases, vendors=vendors
    )


@app.route("/server/models")
def server_models():
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    releases = flask.request.args.getlist("release")
    vendors = flask.request.args.getlist("vendors")

    models_response = api.certifiedmodels(
        category="Server",
        major_release__in=",".join(releases) if releases else None,
        vendor=vendors,
        query=query,
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    vendor_data = api.vendorsummaries_server()["vendors"]

    all_releases = []
    all_vendors = []

    for vendor_datum in vendor_data:
        all_vendors.append(vendor_datum["vendor"])
        for release in vendor_datum["releases"]:
            if release not in all_releases:
                all_releases.append(release)

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "server/models.html",
        models=models,
        query=query,
        releases=releases,
        all_releases=sorted(all_releases, reverse=True),
        vendors=vendors,
        all_vendors=sorted(all_vendors),
        total=total,
        page=page,
        query_string="&".join(query_items),
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/iot")
def iot():
    return flask.render_template(
        "iot/index.html",
        releases=api.certifiedreleases(smart_core__gte="1")["objects"],
        vendors=api.certifiedmakes(smart_core__gte="1")["objects"],
    )


@app.route("/iot/models")
def iot_models():
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    level = flask.request.args.get("level") or "Any"
    releases = flask.request.args.getlist("release")
    vendors = flask.request.args.getlist("vendors")

    if level.lower() == "any":
        level = None

    models_response = api.certifiedmodels(
        level=level,
        category="Ubuntu Core",
        major_release__in=",".join(releases) if releases else None,
        vendor=vendors,
        query=query,
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    all_releases = []
    all_vendors = []

    for release in api.certifiedreleases(smart_core__gte="1")["objects"]:
        all_releases.append(release["release"])

    for vendor in api.certifiedmakes(smart_core__gte="1")["objects"]:
        all_vendors.append(vendor["make"])

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "iot/models.html",
        models=models,
        query=query,
        level=level,
        releases=releases,
        all_releases=sorted(all_releases, reverse=True),
        vendors=vendors,
        all_vendors=sorted(all_vendors),
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/soc")
def soc():
    return flask.render_template(
        "soc/index.html",
        releases=api.certifiedreleases(soc__gte="1")["objects"],
        vendors=api.certifiedmakes(soc__gte="1")["objects"],
    )


@app.route("/soc/models")
def soc_models():
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    releases = flask.request.args.getlist("release")
    vendors = flask.request.args.getlist("vendors")

    models_response = api.certifiedmodels(
        category="Server SoC",
        major_release__in=",".join(releases) if releases else None,
        vendor=vendors,
        query=query,
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    all_releases = []
    all_vendors = []

    for release in api.certifiedreleases(soc__gte="1", limit="0")["objects"]:
        all_releases.append(release["release"])

    for vendor in api.certifiedmakes(soc__gte="1", limit="0")["objects"]:
        all_vendors.append(vendor["make"])

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "soc/models.html",
        models=models,
        query=query,
        releases=releases,
        all_releases=sorted(all_releases, reverse=True),
        vendors=vendors,
        all_vendors=sorted(all_vendors),
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/make/<make>")
def make(make):
    meta = api.certifiedmakes(limit="0", make__iexact=make)["meta"]
    if meta["total_count"] == 0:
        flask.abort(404)

    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    level = flask.request.args.get("level") or "Any"
    categories = flask.request.args.getlist("category") or [
        "Desktop",
        "Laptop",
        "Server",
        "Server SoC",
        "Ubuntu Core",
    ]
    releases = flask.request.args.getlist("release")

    if level.lower() == "any":
        level = None

    models_response = api.certifiedmodels(
        level=level,
        category__in=",".join(categories),
        major_release__in=",".join(releases) if releases else None,
        make__iexact=make,
        query=query,
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    all_categories = [
        "Desktop",
        "Laptop",
        "Server",
        "Server SoC",
        "Ubuntu Core",
    ]
    all_releases = [
        release["release"]
        for release in api.certifiedreleases(limit="0")["objects"]
    ]

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "models.html",
        make=make,
        models=models,
        query=query,
        level=level,
        categories=categories,
        all_categories=all_categories,
        releases=releases,
        all_releases=sorted(all_releases, reverse=True),
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/models")
def models():
    """
    NOTE: if/when the model list pages are redesigned, consider collapsing all
    of the /foo/models paths to a generalized /models handler that uses only a
    generalized models.html template.
    """
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    level = flask.request.args.get("level") or "Any"
    categories = flask.request.args.getlist("category") or [
        "Desktop",
        "Laptop",
        "Server",
        "Server SoC",
        "Ubuntu Core",
    ]
    releases = flask.request.args.getlist("release")
    vendors = flask.request.args.getlist("vendors")

    if level.lower() == "any":
        level = None

    models_response = api.certifiedmodels(
        level=level,
        category__in=",".join(categories),
        major_release__in=",".join(releases) if releases else None,
        vendor=vendors,
        query=query,
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    all_categories = [
        "Desktop",
        "Laptop",
        "Server",
        "Server SoC",
        "Ubuntu Core",
    ]
    all_releases = [
        release["release"]
        for release in api.certifiedreleases(limit="0")["objects"]
    ]
    all_vendors = [
        vendor["make"] for vendor in api.certifiedmakes(limit="0")["objects"]
    ]

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "models.html",
        models=models,
        query=query,
        level=level,
        categories=categories,
        all_categories=all_categories,
        releases=releases,
        all_releases=sorted(all_releases, reverse=True),
        vendors=vendors,
        all_vendors=sorted(all_vendors),
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/components")
def components():
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")
    canonical_id = flask.request.args.get("canonical_id")
    vendors = flask.request.args.getlist("vendor")

    components_response = api.componentsummaries(
        make=vendors,
        query=query,
        offset=(int(page) - 1) * 20,
        canonical_id=canonical_id,
    )
    components = components_response["objects"]
    total = components_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    all_vendors = ["AMD", "Lenovo", "nVidia"]

    params = flask.request.args.copy()
    params.pop("page", None)
    query_items = []
    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "components/index.html",
        components=components,
        query=query,
        vendors=vendors,
        all_vendors=sorted(all_vendors),
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/components/<id>")
def component_details(id):
    component = api.componentsummary(id)

    all_machines = api.certifiedmodels(
        canonical_id__in=component["machine_canonical_ids"]
    )["objects"]

    machines_by_id = {}

    for machine in all_machines:
        if machine["canonical_id"] not in machines_by_id:
            machines_by_id[machine["canonical_id"]] = machine

    machines = machines_by_id.values()

    return flask.render_template(
        "components/details.html",
        component=component,
        machines=sorted(
            machines, key=lambda machine: machine["canonical_id"], reverse=True
        ),
    )


@app.route("/catalog/component/<identifier>")
@app.route("/catalog/component/<subsystem>/<identifier>")
def catalog_component(identifier, subsystem=None):
    page = int(flask.request.args.get("page") or "1")

    devices = api.certifiedmodeldevices(
        identifier=identifier.replace("---", "/"), subsystem=subsystem, limit=0
    )["objects"]

    if not devices:
        flask.abort(404)

    canonical_ids = [device["canonical_id"] for device in devices]

    # Only get the first 267 canonical_ids, as the URL will be too long
    # otherwise
    models_response = api.certifiedmodels(
        canonical_id__in=",".join(canonical_ids[:267]),
        offset=(int(page) - 1) * 20,
    )
    models = models_response["objects"]
    total = models_response["meta"]["total_count"]
    num_pages = math.ceil(total / 20)

    return flask.render_template(
        "catalog/component.html",
        device=devices[0],
        models=models,
        total=total,
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )


@app.route("/catalog/search")
def catalog_search():
    query = flask.request.args.get("query") or ""
    page = int(flask.request.args.get("page") or "1")

    devices_response = api.certifiedmodeldevices(
        query=query, offset=(int(page) - 1) * 20
    )

    devices = devices_response["objects"]
    total = devices_response["meta"]["total_count"]

    num_pages = math.ceil(total / 20)

    params = flask.request.args.copy()
    params.pop("page", None)

    query_items = []

    for key, valuelist in params.lists():
        for value in valuelist:
            query_items.append(f"{key}={value}")

    return flask.render_template(
        "catalog/search.html",
        devices=devices,
        query=query,
        total=total,
        query_string="&".join(query_items),
        page=page,
        pages=get_pagination_page_array(page, num_pages),
    )
