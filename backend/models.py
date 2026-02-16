from pydantic import BaseModel


class AnalyzeRequest(BaseModel):
    target_item: str
    target_rate: float
    excluded_recipes: list[str] = []
    max_factories: int = 8


class LocationTheme(BaseModel):
    theme_id: str
    critical_resources: dict[str, float]


class LocationsRequest(BaseModel):
    themes: list[LocationTheme]
    search_radius_m: float = 500
    excluded_quadrants: list[str] = []
    n_results: int = 3


class AllocateFactory(BaseModel):
    theme_id: str
    demands_per_unit: dict[str, float]
    local_capacity: dict[str, float]


class AllocateRequest(BaseModel):
    factories: list[AllocateFactory]
    target_rate: float
    train_penalty: float = 2.0
    water_penalty: float = 3.0


class GenerateFactory(BaseModel):
    theme_id: str
    target_item: str
    excluded_recipes: list[str]
    allocated_rate: float
    local_resources: dict[str, float]


class GenerateRequest(BaseModel):
    factories: list[GenerateFactory]
