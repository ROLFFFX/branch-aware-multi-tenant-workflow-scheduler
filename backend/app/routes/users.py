from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.services.user_manager import UserManager

router = APIRouter(prefix="/users", tags=["Users"])

class UserCreateRequest(BaseModel):
    user_id: str    # uuid from client
    
@router.post("/", summary="Register a new user")
async def register_user(payload: UserCreateRequest):
    user_id = payload.user_id

    is_registered = await UserManager.is_registered(user_id)
    if is_registered:
        raise HTTPException(status_code=400, detail="User already exists.")

    await UserManager.register_user(user_id)
    return {"message": "User registered successfully.", "user_id": user_id}


@router.delete("/{user_id}", summary="Delete an existing user")
async def delete_user(user_id: str):
    deleted = await UserManager.delete_user(user_id)

    if not deleted:
        raise HTTPException(status_code=404, detail="User not found.")

    return {"message": "User deleted successfully.", "user_id": user_id}

@router.get("/", summary="Get all userIDs")
async def list_users():
    users = await UserManager.get_all_users()
    return {"count": len(users), "users": list(users)}