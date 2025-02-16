class CertificationAPI:
    """
    Method names and properties to describe and map directly
    onto the Certification API
    (at the time of writing, this API is available at
    https://certification.canonical.com/api/v1)
    """

    def __init__(self, base_url, session):
        self.base_url = base_url
        self.session = session

    def _get(self, path, params={}):
        # Remove "None" values from params
        params = {
            key: value for key, value in params.items() if value is not None
        }

        # Get the JSON data
        response = self.session.get(
            f"{self.base_url}/{path.strip('/')}/?format=json", params=params
        )

        # Raise any HTTP errors
        response.raise_for_status()

        return response

    def certifiedmakes(
        self,
        limit=None,
        offset=None,
        desktops__gte=None,
        laptops__gte=None,
        smart_core__gte=None,
        soc__gte=None,
        make__iexact=None,
    ):
        return self._get(
            "certifiedmakes",
            params={
                "limit": limit,
                "offset": offset,
                "desktops__gte": desktops__gte,
                "laptops__gte": laptops__gte,
                "smart_core__gte": smart_core__gte,
                "soc__gte": soc__gte,
                "make__iexact": make__iexact,
            },
        ).json()

    def certifiedmodels(
        self,
        limit=None,
        offset=None,
        level=None,
        category=None,
        canonical_id=None,
        canonical_id__in=None,
        major_release__in=None,
        vendor=None,
        make__iexact=None,
        query=None,
        category__in=None,
        order_by=None,
    ):
        response = self._get(
            "certifiedmodels",
            params={
                "limit": limit,
                "offset": offset,
                "level": level,
                "major_release__in": major_release__in,
                "vendor": vendor,
                "make__iexact": make__iexact,
                "query": query,
                "canonical_id": canonical_id,
                "canonical_id__in": canonical_id__in,
                "category": category,
                "category__in": category__in,
                "order_by": order_by,
            },
        )
        response.raise_for_status()

        return response.json()

    def certifiedmodeldetails(
        self, limit=None, offset=None, canonical_id=None
    ):
        return self._get(
            "certifiedmodeldetails",
            params={
                "limit": limit,
                "offset": offset,
                "canonical_id": canonical_id,
            },
        ).json()

    def certifiedmodeldevices(
        self,
        limit=None,
        offset=None,
        query=None,
        canonical_id=None,
        identifier=None,
        subsystem=None,
    ):
        return self._get(
            "certifiedmodeldevices",
            params={
                "limit": limit,
                "offset": offset,
                "query": query,
                "canonical_id": canonical_id,
                "identifier": identifier,
                "subsystem": subsystem,
            },
        ).json()

    def certifiedreleases(
        self, limit=None, offset=None, smart_core__gte=None, soc__gte=None
    ):
        return self._get(
            "certifiedreleases",
            params={
                "limit": limit,
                "offset": offset,
                "smart_core__gte": smart_core__gte,
                "soc__gte": soc__gte,
            },
        ).json()

    def componentsummaries(
        self,
        limit=None,
        offset=None,
        id=None,
        canonical_id=None,
        query=None,
        make=None,
    ):
        return self._get(
            "componentsummaries",
            params={
                "limit": limit,
                "offset": offset,
                "id": id,
                "canonical_id": canonical_id,
                "query": query,
                "make": make,
            },
        ).json()

    def componentsummary(self, id):
        return self._get(f"componentsummaries/{id}").json()

    def devicecategories(self, limit=None, offset=None):
        return self._get(
            "devicecategories", params={"limit": limit, "offset": offset}
        ).json()

    def releases(self, limit=None, offset=None):
        return self._get(
            "releases", params={"limit": limit, "offset": offset}
        ).json()

    def vendorsummaries_server(self, limit=None, offset=None):
        return self._get(
            "vendorsummaries/server", params={"limit": limit, "offset": offset}
        ).json()
