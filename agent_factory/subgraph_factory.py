from typing import Dict,Any,List,Optional,Type
from langgraph.graph import StateGraph,START
from langchain_core.messages import HumanMessage,AIMessage,SystemMessage,BaseMessage

from observability.basic_observability import timed_hook
from observability.ot_observability import traced
from observability.logging_setup import get_logger,init_logging

init_logging(level="INFO",log_file="MAF.log")
logger = get_logger("MAF")

def _normalize_schema(schema:Optional[Type]) -> Type:
    if schema is None:
        return dict
    if isinstance(schema,dict):
        raise TypeError(
            "state_schema must be a TYPE (e.g., dict, TypedDict, etc.)."
        )
    return schema

class SubgraphBrain:

    def __init__(
        self,
        name: str,
        prompt: str,
        tools: List[Any],
        state_mgr: Optional[StateManger] = None,
        scope: Optional[str] = None,
    ):
        self.name = name
        self.prompt = prompt
        self.tools = tools
        self.state_mgr = state_mgr
        self.scope = scope or name
        self.llm = get_shared_llm()
        self.llm_with_tools = self.llm.bind_tools(self.tools)

    @traced(span_name="SubgraphBrain.call",with_args=True)
    @timed_hook("SubgraphBrain.call")
    async def __call__(
        self,
        state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            logger.info(f"SubgraphBrain '{self.name}' called with state: {state}")
            ctx = state.get("__context",{})
            user_query = " ".join(state.get("plan"))

            msgs = [
                SystemMessage(content=self.prompt),
                SystemMessage(content=f"Shared Context: {ctx}"),
                HumanMessage(content=user_query),
            ]
            response = await self.llm_with_tools.ainvoke(msgs)
            result = {
                "message": [response],
                "llm_response": response,
            }

            if self.state_mgr:
                self.state_mgr.update_state(self.scope,{
                    "raw_response": response,
                    "query": user_query,
                    "used_context": ctx,
                })

            return result
        except Exception as e:
            logger.error(f"Error in SubgraphBrain '{self.name}': {e}")
            err = {"messages":[f"Error: {str(e)}"]}
            if self.state_mgr:
                self.state_mgr.update_state(self.scope,{
                    "error": str(e),
                    "query": user_query,
                    "used_context": ctx,
                })
            return err
        

class SubgraphFactory:

    def __init__(
            self,
            name: str,
            description: str,
            prompt: str,
            tools: Optional[List[Any]],
            state_mgr: Optional[StateManger] = None,
            state_schema: Optional[Type] = None,
            scope: Optional[str] = None,
            ):
        self.name = name
        self.description = description
        self.prompt = prompt
        self.tools = tools or []
        self.state_mgr = state_mgr
        self.state_schema = _normalize_schema(state_schema)
        self.scope = scope or name

        logger.info(f"SubgraphFactory '{self.name}' initialized with description: {self.description}")
        self.graph = self._create_subgraph()

        # later register the subgraph in a global registry if needed

        SubgraphRegistry.register(
            self.name,
            {
                "name": self.name,
                "description": self.description,
                "graph": self.graph,
                "state_schema": self.state_schema,
                "scope": self.scope,
                "tools": self.tools,
                "prompt": self.prompt,
                "state_mgr": self.state_mgr,
            }
        )
        logger.info(f"SubgraphFactory '{self.name}' registered in SubgraphRegistry.")

    def _create_subgraph(self) -> StateGraph:
        self.brain = SubgraphBrain(
            name=self.name,
            prompt=self.prompt,
            tools=self.tools,
            state_mgr=self.state_mgr,
            scope=self.scope,
        )

        graph = StateGraph(self.state_schema)
        graph.add_node("brain", brain)