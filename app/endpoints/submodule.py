from fastapi import APIRouter

router = APIRouter()

@router.get("/submodule")
def read_root():
    return {"Hello": "submodule"}

