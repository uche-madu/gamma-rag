from pydantic import BaseModel, ConfigDict, Field

class ChatRequest(BaseModel):
    query: str = Field(..., min_length=1, max_length=600, description="User's financial query.")

    model_config = ConfigDict(
        str_strip_whitespace=True
    )


class ChatResponse(BaseModel):
    response: str

    model_config = ConfigDict(
        str_strip_whitespace=True
    )
