from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from supertokens_python.recipe.session import SessionContainer
from supertokens_python.recipe.session.framework.fastapi import verify_session

router = APIRouter(prefix="/me")


@router.get("")
async def me(session_: SessionContainer = Depends(verify_session())) -> JSONResponse:
    return JSONResponse({"userId": session_.get_user_id()})
