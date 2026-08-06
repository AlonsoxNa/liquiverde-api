from dataclasses import dataclass

from app.domain.product import Product


@dataclass(frozen=True)
class OptimizationCandidate:
    product: Product
    total_score: float
    utility: float
    unit_co2e_kg: float


@dataclass(frozen=True)
class NeedOptions:
    category: str
    quantity: int
    reference: OptimizationCandidate
    candidates: tuple[OptimizationCandidate, ...]


@dataclass(frozen=True)
class OptimizedSelection:
    need: NeedOptions
    candidate: OptimizationCandidate | None


@dataclass(frozen=True)
class OptimizationOutcome:
    selections: tuple[OptimizedSelection, ...]
    optimized_cost: int
    optimized_co2e_kg: float
    aggregate_utility: float
    aggregate_score: float

    @property
    def uncovered_categories(self) -> tuple[str, ...]:
        return tuple(
            selection.need.category
            for selection in self.selections
            if selection.candidate is None
        )


@dataclass(frozen=True)
class _State:
    cost: int
    utility: float
    covered: int
    selections: tuple[OptimizationCandidate | None, ...]


def optimize_needs(
    needs: tuple[NeedOptions, ...],
    budget_clp: int,
) -> OptimizationOutcome:
    states = {0: _State(cost=0, utility=0, covered=0, selections=())}
    for need in needs:
        next_states: dict[int, _State] = {}
        for state in states.values():
            _store_state(
                next_states,
                _State(
                    cost=state.cost,
                    utility=state.utility,
                    covered=state.covered,
                    selections=(*state.selections, None),
                ),
            )
            for candidate in need.candidates:
                candidate_cost = candidate.product.price_clp * need.quantity
                total_cost = state.cost + candidate_cost
                if total_cost > budget_clp:
                    continue
                _store_state(
                    next_states,
                    _State(
                        cost=total_cost,
                        utility=state.utility + candidate.utility * need.quantity,
                        covered=state.covered + 1,
                        selections=(*state.selections, candidate),
                    ),
                )
        states = _remove_dominated_states(next_states)
    best_state = next(iter(states.values()))
    for state in states.values():
        if _is_better(state, best_state, compare_cost=True):
            best_state = state
    selections = tuple(
        OptimizedSelection(need=need, candidate=candidate)
        for need, candidate in zip(needs, best_state.selections, strict=True)
    )
    optimized_co2e = sum(
        selection.candidate.unit_co2e_kg * selection.need.quantity
        for selection in selections
        if selection.candidate is not None
    )
    covered_units = sum(
        selection.need.quantity
        for selection in selections
        if selection.candidate is not None
    )
    weighted_score = sum(
        selection.candidate.total_score * selection.need.quantity
        for selection in selections
        if selection.candidate is not None
    )
    return OptimizationOutcome(
        selections=selections,
        optimized_cost=best_state.cost,
        optimized_co2e_kg=optimized_co2e,
        aggregate_utility=best_state.utility,
        aggregate_score=weighted_score / covered_units if covered_units else 0,
    )


def _store_state(states: dict[int, _State], candidate: _State) -> None:
    existing = states.get(candidate.cost)
    if existing is None or _is_better(candidate, existing, compare_cost=False):
        states[candidate.cost] = candidate


def _remove_dominated_states(states: dict[int, _State]) -> dict[int, _State]:
    retained: dict[int, _State] = {}
    for cost in sorted(states):
        candidate = states[cost]
        is_dominated = any(
            state.covered >= candidate.covered and state.utility >= candidate.utility
            for state in retained.values()
        )
        if not is_dominated:
            retained[cost] = candidate
    return retained


def _is_better(left: _State, right: _State, compare_cost: bool) -> bool:
    if left.covered != right.covered:
        return left.covered > right.covered
    if left.utility != right.utility:
        return left.utility > right.utility
    if compare_cost and left.cost != right.cost:
        return left.cost < right.cost
    return _selection_ids(left) < _selection_ids(right)


def _selection_ids(state: _State) -> tuple[str, ...]:
    return tuple(
        candidate.product.id if candidate is not None else ""
        for candidate in state.selections
    )
