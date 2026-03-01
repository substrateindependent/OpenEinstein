# Model Routing

## Purpose

The routing subsystem maps logical model roles (`reasoning`, `generation`, `fast`, `embeddings`) to provider/model configurations.

## Interfaces

- `ModelRouter.resolve(role) -> ModelConfig`
- `ModelRouter.run_with_fallback(role, call)`
- `load_routing_config(path) -> RoutingConfig`

## Invariants

- Feature logic must reference only logical roles.
- Fallbacks are deterministic and ordered.
- Token/cost usage is tracked per role.
