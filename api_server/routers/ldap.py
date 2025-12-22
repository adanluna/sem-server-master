from fastapi import APIRouter, HTTPException
from api_server.schemas import LDAPLoginRequest
from services.ldap_service import ldap_authenticate, ldap_user_info

router = APIRouter()


@router.post("/ldap")
def auth_ldap(data: LDAPLoginRequest):
    result = ldap_authenticate(data.username, data.password)

    if not result["success"]:
        raise HTTPException(status_code=401, detail=result["message"])

    return result


@router.get("/ldap/userinfo/{username}")
def userinfo(username: str):
    return ldap_user_info(username)
