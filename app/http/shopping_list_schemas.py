from pydantic import BaseModel, Field, model_validator

from app.http.product_schemas import ProductResponse


class ShoppingNeedRequest(BaseModel):
    reference_product_id: str = Field(min_length=1, max_length=64)
    quantity: int = Field(ge=1, le=99)


class OptimizationPreferencesRequest(BaseModel):
    economic: float = Field(default=40, ge=0)
    environmental: float = Field(default=40, ge=0)
    social: float = Field(default=20, ge=0)

    @model_validator(mode="after")
    def require_positive_weight(self) -> OptimizationPreferencesRequest:
        if self.economic + self.environmental + self.social == 0:
            raise ValueError("Al menos una prioridad debe ser mayor que cero.")
        return self


class OptimizeShoppingListRequest(BaseModel):
    budget_clp: int = Field(ge=1, le=1_000_000)
    needs: list[ShoppingNeedRequest] = Field(min_length=1, max_length=6)
    preferences: OptimizationPreferencesRequest = Field(
        default_factory=OptimizationPreferencesRequest
    )


class OptimizedSelectionResponse(BaseModel):
    category: str
    quantity: int
    reference_product: ProductResponse
    selected_product: ProductResponse | None
    cost_clp: int
    score: float | None
    co2e_kg: float
    reason: str


class OptimizationSummaryResponse(BaseModel):
    budget_clp: int
    reference_cost_clp: int
    optimized_cost_clp: int
    savings_clp: int
    savings_percentage: float
    reference_co2e_kg: float
    optimized_co2e_kg: float
    avoided_co2e_kg: float
    aggregate_utility: float
    aggregate_score: float
    uncovered_categories: list[str]


class OptimizeShoppingListResponse(BaseModel):
    selections: list[OptimizedSelectionResponse]
    summary: OptimizationSummaryResponse
