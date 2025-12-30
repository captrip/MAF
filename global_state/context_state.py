from typing import Dict,Any,Iterable,Tuple
from copy import deepcopy


class Context:
    def __init__(self, initial_state: Dict[str, Any] = None):
        self.state: Dict[str, Any] = deepcopy(initial_state or {})

    def get(self, key: str, default: Any = None) -> Any:
        return self.state.get(key, default)

    def set(self, key: str, value: Any) -> "Context":
        self.state[key] = value
        return self
    def update(self, updates: Dict[str, Any]) -> "Context":
        self.state.update(updates)
        return self

    def to_dict(self) -> Dict[str, Any]:
        return dict(self.state)

    def copy(self) -> "Context":
        return Context(deepcopy(self.state))
    
    def get_scope(self, scope: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        value = self.state.get(scope, default)
        if isinstance(value, dict):
            return dict(value)
        
        return value
    
    def set_scope(self, scope: str, value: Dict[str, Any]) -> "Context":
        self.state[scope] = dict(value)
        return self