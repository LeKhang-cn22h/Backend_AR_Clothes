from fastapi import APIRouter, Request

router = APIRouter()

_item_index: int = 0

@router.post("/api/lens-params")
async def set_lens_params(request: Request):
    global _item_index
    body = await request.json()
    _item_index = int(body.get("item_index", 0))
    print(f"[lens-params] SET item_index = {_item_index}")
    return {"ok": True, "item_index": _item_index}

@router.get("/api/lens-params")
async def get_lens_params():
    print(f"[lens-params] GET item_index = {_item_index}")
    return {"item_index": _item_index}