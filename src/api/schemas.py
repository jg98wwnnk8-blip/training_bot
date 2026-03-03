from pydantic import BaseModel


class WebAppAuthRequest(BaseModel):
    initData: str


class WebAppAuthResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int
    user_id: int
