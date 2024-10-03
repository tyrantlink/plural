from pydantic import BaseModel
from tomllib import loads


class Project(BaseModel):
    bot_token: str
    mongo_uri: str
    base_url: str


with open('project.toml', 'r') as f:
    project = Project.model_validate(loads(f.read()))
