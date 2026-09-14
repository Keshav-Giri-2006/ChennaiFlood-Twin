from __future__ import annotations

from fastapi import APIRouter, Depends, Path, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from app.api.deps import get_container
from app.core.container import Container
from app.schemas.api import GisCatalogueResponse
from app.schemas.common import ErrorResponse

router = APIRouter(prefix="/gis", tags=["gis"])

GEOJSON = "application/geo+json"
_ERRORS = {404: {"model": ErrorResponse}, 503: {"model": ErrorResponse}}


def _serve(layer: str, request: Request, container: Container) -> Response:
    path, manifest = container.gis.layer(layer)
    etag = f'"{manifest["assetSha256"]}"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=3600"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return FileResponse(path, media_type=GEOJSON, headers=headers)


_GEOJSON_DOC = {200: {"content": {GEOJSON: {}}, "description": "RFC 7946 GeoJSON FeatureCollection (lon/lat) with a `metadata` member."}, **_ERRORS}


@router.get("", response_model=GisCatalogueResponse, summary="List available GIS layers")
def catalogue(container: Container = Depends(get_container)) -> dict:
    return {"layers": container.gis.catalogue()}


@router.get("/terrain", responses=_ERRORS, summary="Ward 176 DEM grid (Copernicus GLO-30) for web terrain")
def terrain(request: Request, container: Container = Depends(get_container)) -> Response:
    grid, sha = container.gis.terrain()
    etag = f'"{sha}"'
    headers = {"ETag": etag, "Cache-Control": "public, max-age=3600"}
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers=headers)
    return JSONResponse(grid, headers=headers)


@router.get("/ward", responses=_GEOJSON_DOC, response_class=Response, summary="Ward 176 boundary")
def ward(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("ward", request, container)


@router.get("/buildings", responses=_GEOJSON_DOC, response_class=Response, summary="Ward 176 building footprints")
def buildings(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("buildings", request, container)


@router.get("/roads", responses=_GEOJSON_DOC, response_class=Response, summary="Ward 176 carriageways")
def roads(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("roads", request, container)


@router.get("/drains", responses=_GEOJSON_DOC, response_class=Response, summary="Ward 176 storm-water drains (GCC source features)")
def drains(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("drains", request, container)


@router.get("/drains/{objectId}", responses=_ERRORS, summary="Source drain detail")
def drain_detail(objectId: int = Path(ge=1), container: Container = Depends(get_container)) -> dict:
    return container.gis.drain(objectId)


@router.get("/subcatchments", responses=_GEOJSON_DOC, response_class=Response, summary="SWMM model subcatchments (model constructs)")
def subcatchments(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("subcatchments", request, container)


@router.get("/model/conduits", responses=_GEOJSON_DOC, response_class=Response, summary="SWMM model conduit geometry")
def model_conduits(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("model-conduits", request, container)


@router.get("/model/nodes", responses=_GEOJSON_DOC, response_class=Response, summary="SWMM model node locations")
def model_nodes(request: Request, container: Container = Depends(get_container)) -> Response:
    return _serve("model-nodes", request, container)
