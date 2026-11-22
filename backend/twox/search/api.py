"""Search API (work order 052): ``GET /api/v1/search/``.

The endpoint passes the query to the search interface
(:func:`twox.search.interface.get_search_backend`, 047 and 050) and returns
its hits as plain data; it runs no SQL of its own. Both roles may search
(``CanRead``, E-40); there are no rights per device in M2.

Parameters (query string): ``q`` (required, 1 to :data:`MAX_QUERY_CHARS`
characters after trimming white space), ``device`` and ``plant`` (ids,
each repeatable, at most :data:`MAX_FILTER_IDS` values; a hit must lie on
one of the devices and in one of the plants) and ``limit`` (1 to
:data:`MAX_HITS`, default :data:`DEFAULT_HITS`). An invalid value gives 400
with an error at the field.

The answer says in ``semantic`` whether the search by meaning took part:
``used``; ``disabled`` when the AI features are off (E-59, a normal state,
not an error); ``unavailable`` when the model service failed and the hits
come from the keyword search only. Each hit names its section, score, how it
was found, a plain-text snippet with the found places (``highlights``,
positions in Unicode code points of the snippet, not UTF-16 units), pages,
headings and all places it is stored at (document, version, device, plant).
No whole section, no HTML: the client sets the highlights itself.

The search text is never logged or stored: the view logs nothing, and the
filter in :mod:`twox.config.logging` cuts query strings off uvicorn's access
log.
"""

from typing import Any, Final

from drf_spectacular.utils import OpenApiResponse, extend_schema
from rest_framework import serializers
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from twox.accounts.permissions import CanRead
from twox.assets.views import MAX_ID
from twox.files.serializers import ErrorDetailSerializer
from twox.search.interface import (
    MatchKind,
    SearchHit,
    SearchRequest,
    SearchResult,
    SemanticState,
    get_search_backend,
)

#: Longest query, in characters after trimming.
MAX_QUERY_CHARS: Final = 500
#: Hits per answer when ``limit`` is not given, and the largest ``limit``.
DEFAULT_HITS: Final = 20
MAX_HITS: Final = 50
#: Most ids in ``device`` or in ``plant``.
MAX_FILTER_IDS: Final = 100


def _id_list(description: str) -> serializers.ListField:
    return serializers.ListField(
        child=serializers.IntegerField(min_value=1, max_value=MAX_ID),
        required=False,
        default=list,
        max_length=MAX_FILTER_IDS,
        help_text=description,
    )


class SearchParametersSerializer(serializers.Serializer[Any]):
    """The query parameters of the search."""

    q = serializers.CharField(
        max_length=MAX_QUERY_CHARS,
        help_text=(
            "What to search for: words, identifiers such as IP addresses or part numbers, "
            'or a question. "-word" excludes a word, "two words" in quotes is a phrase.'
        ),
    )
    device = _id_list("Only hits on one of these devices (ids); repeat the parameter for more.")
    plant = _id_list("Only hits in one of these plants (ids); repeat the parameter for more.")
    limit = serializers.IntegerField(
        min_value=1,
        max_value=MAX_HITS,
        default=DEFAULT_HITS,
        help_text="Most hits in the answer.",
    )


class SearchDocumentSerializer(serializers.Serializer[Any]):
    """The document a hit is stored in."""

    id = serializers.IntegerField()
    title = serializers.CharField()


class SearchVersionSerializer(serializers.Serializer[Any]):
    """The document version a hit is stored in."""

    id = serializers.IntegerField()
    number = serializers.IntegerField()
    original_filename = serializers.CharField()
    is_latest = serializers.BooleanField(
        help_text=(
            "False when the document has a newer version that is not searchable yet "
            "(not ingested, or ingesting it failed)."
        )
    )


class SearchDeviceSerializer(serializers.Serializer[Any]):
    """The device the document of a hit belongs to."""

    id = serializers.IntegerField()
    key = serializers.CharField()
    name = serializers.CharField()


class SearchPlantSerializer(serializers.Serializer[Any]):
    """The plant of the device of a hit."""

    id = serializers.IntegerField()
    key = serializers.CharField()
    name = serializers.CharField()


class SearchLocationSerializer(serializers.Serializer[Any]):
    """One place a hit is stored at."""

    document = SearchDocumentSerializer()
    version = SearchVersionSerializer()
    device = SearchDeviceSerializer()
    plant = SearchPlantSerializer()


class SearchHighlightSerializer(serializers.Serializer[Any]):
    """A found place in the snippet: ``snippet[start:end]`` in Unicode code points."""

    start = serializers.IntegerField()
    end = serializers.IntegerField()


class SearchHitSerializer(serializers.Serializer[Any]):
    """One found piece of text with every place it is stored at."""

    section_id = serializers.IntegerField()
    score = serializers.FloatField(help_text="Higher is better; only the order matters.")
    match_kinds = serializers.ListField(
        child=serializers.ChoiceField(choices=[kind.value for kind in MatchKind]),
        help_text="How the hit was found: exact identifier, keyword, meaning.",
    )
    snippet = serializers.CharField(
        help_text="Plain text around the first found place, about 300 characters; not HTML."
    )
    highlights = SearchHighlightSerializer(many=True)
    page_start = serializers.IntegerField(allow_null=True)
    page_end = serializers.IntegerField(allow_null=True)
    heading_path = serializers.ListField(child=serializers.CharField())
    locations = SearchLocationSerializer(many=True)


class SearchResultSerializer(serializers.Serializer[Any]):
    """The hits of a search, best first."""

    semantic = serializers.ChoiceField(
        choices=[state.value for state in SemanticState],
        help_text=(
            "Whether the search by meaning took part: used; disabled (AI features off, "
            "a normal state); unavailable (model service failed, keyword search only)."
        ),
    )
    hits = SearchHitSerializer(many=True)


def hit_data(hit: SearchHit) -> dict[str, Any]:
    """``hit`` in the shape of :class:`SearchHitSerializer`."""
    return {
        "section_id": hit.section_id,
        "score": hit.score,
        "match_kinds": [str(kind) for kind in hit.match_kinds],
        "snippet": hit.snippet,
        "highlights": [{"start": h.start, "end": h.end} for h in hit.highlights],
        "page_start": hit.page_start,
        "page_end": hit.page_end,
        "heading_path": list(hit.heading_path),
        "locations": [
            {
                "document": {"id": loc.document_id, "title": loc.document_title},
                "version": {
                    "id": loc.version_id,
                    "number": loc.version_number,
                    "original_filename": loc.version_filename,
                    "is_latest": loc.is_latest_version,
                },
                "device": {"id": loc.device_id, "key": loc.device_key, "name": loc.device_name},
                "plant": {"id": loc.plant_id, "key": loc.plant_key, "name": loc.plant_name},
            }
            for loc in hit.locations
        ],
    }


def result_data(result: SearchResult) -> dict[str, Any]:
    """``result`` in the shape of :class:`SearchResultSerializer`."""
    return {"semantic": str(result.semantic), "hits": [hit_data(hit) for hit in result.hits]}


class SearchView(APIView):
    """Search the ingested documents."""

    permission_classes = (CanRead,)

    @extend_schema(
        operation_id="search",
        parameters=[SearchParametersSerializer],
        responses={
            200: SearchResultSerializer,
            400: OpenApiResponse(description="Invalid parameter; the errors are per field."),
            403: OpenApiResponse(ErrorDetailSerializer, description="No role."),
        },
    )
    def get(self, request: Request) -> Response:
        """Hits for ``q``, best first, at most ``limit``; optionally only on some devices or plants.

        Exact identifiers come first, then keyword and meaning together.
        The same content stored for several devices is one hit with all its
        places.
        """
        parameters = SearchParametersSerializer(data=request.query_params)
        parameters.is_valid(raise_exception=True)
        values = parameters.validated_data
        search = SearchRequest(
            query=values["q"],
            device_ids=tuple(values["device"]),
            plant_ids=tuple(values["plant"]),
            limit=values["limit"],
        )
        result = get_search_backend().search(search)
        return Response(SearchResultSerializer(result_data(result)).data)
