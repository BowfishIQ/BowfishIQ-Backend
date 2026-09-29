from fastapi import APIRouter, Body, Depends, File, Form, Request, UploadFile
import Services.userService as userService
from Models.User import UserModel, UserUpdateModel
from Services.common import save_file
from typing import Optional

router = APIRouter()


@router.post("/users/", tags=["USER MANAGEMENT"])
async def create_user(
    request: Request,
    user_data: UserModel = Body(...),
):
    return userService.create(request, user_data)


@router.get("/users/{page}", tags=["USER MANAGEMENT"])
def get_all(
    page: int,
    limit: int,
    role: Optional[int] = None,
    user_id: Optional[str] = None,
    status: Optional[int] = None,
    verify_status: Optional[int] = None,
    search_query: Optional[str] = None,
):
    return userService.get_all(
        page, limit, role, user_id, status, verify_status, search_query
    )


@router.get("/get-users-by-token", tags=["USER MANAGEMENT"])
def get_user_by_token(
    request: Request, token: dict = Depends(userService.get_current_user)
):
    if "_id" in token:
        return userService.get_user_by_id(request, str(token["_id"]))
    else:
        return {"message": "Please Login First", "status": "error"}


@router.put("/users", tags=["USER MANAGEMENT"])
async def update_user(
    user_data: UserUpdateModel = Body(...),
    profile_image: Optional[UploadFile] = File(None),
    token: dict = Depends(userService.get_current_user),
):
    try:
        if "_id" in token:
            if profile_image is not None and profile_image != "":
                file = await save_file(profile_image, "uploads/users")
                user_data.profile_image = file
            return userService.update(user_data, str(token["_id"]))
        else:
            return {"message": "Please Login First", "status": "error"}
    except Exception as e:
        return {"error": str(e)}


@router.put("/users-updated-by-superadmin/{id}", tags=["USER MANAGEMENT"])
async def update_user_by_superadmin(
    id: str,
    user_data: UserUpdateModel = Body(...),
    profile_image: Optional[UploadFile] = File(None),
):
    try:

        if profile_image is not None and profile_image != "":
            file = await save_file(profile_image, "uploads/users")
            user_data.profile_image = file
        return userService.update(user_data, str(id))

    except Exception as e:
        return {"error": str(e)}


@router.post("/users/login/", tags=["USER AUTHENTICATION"])
def login_user(
    request: Request,
    email: Optional[str] = Body(None),
    firebase_token: Optional[str] = Body(None),
    login_type: Optional[int] = Body(None),
    google_id: Optional[str] = Body(None),
    password: Optional[str] = Body(None),
):
    return userService.login(
        request,
        email=email,
        firebase_token=firebase_token,
        login_type=login_type,
        google_id=google_id,
        password=password,
    )


@router.post("/users/admin-login/", tags=["USER AUTHENTICATION"])
def admin_login(request: Request, email: str = Body(...), password: str = Body(...)):
    return userService.admin_login(request, email, password)


@router.post("/get-token")
async def login_for_access_token(
    request: Request, username: str = Form(...), password: str = Form(...)
):
    return userService.login(
        request, email=username, password=password, login_type=2
    )
