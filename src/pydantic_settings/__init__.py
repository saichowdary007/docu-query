from pydantic import BaseModel

class SettingsConfigDict(dict):
    pass

class BaseSettings(BaseModel):
    model_config: SettingsConfigDict = SettingsConfigDict()
