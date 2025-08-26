# ===============================================


from typing import List

from pydantic import BaseModel, ConfigDict


class Template(BaseModel):
    model_config = ConfigDict(extra="allow")
    name: str
    filename: str
    iconCode: str
    categories: List[str]


class Templates(BaseModel):
    templates: List[Template]
