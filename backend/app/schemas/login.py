# app/schemas/login.py

from pydantic import BaseModel

class LoginRequest(BaseModel):
    username: str
    password: str
