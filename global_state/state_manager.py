from typing import Callable, Dict, List, Any, Optional,Union,Literal
from dataclasses import dataclass, field,asdict
from datetime import datetime
from enum import Enum
import threading
import json
from copy import deepcopy
import logging
from global_state.context_state import Context

try:
    from langchain_core.messages import HumanMessage, AIMessage, SystemMessage, BaseMessage,ToolMessage
    LANGCHAIN_AVAILABLE = True
except ImportError:
    LANGCHAIN_AVAILABLE = False
    BaseMessage = Any

logger  = logging.getLogger(__name__)

class MessageType(str,Enum):
    HUMAN = "human"
    AI = "ai"
    SYSTEM = "system"
    TOOL = "tool"
    FUNCTION = "function"

@dataclass
class SerializableMessage:
    type: MessageType
    content: str
    timestamp:str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str,Any] = field(default_factory=dict)
    additional_kwargs: Dict[str, Any] = field(default_factory=dict)

    #Agent context
    from_agent: Optional[str] = None
    to_agent: Optional[str] = None
    conversation_id: Optional[str] = None

    #tool
    tool_call_id:Optional[str]= None
    tool_name:Optional[str]= None
    tool_output:Optional[str]= None


def to_dict(self)-> Dict[str,Any]:
    return asdict(self)

@classmethod
def from_dict(cls,data: Dict[str,Any])-> "SerializableMessage":
    return cls(**data)

def to_langchain(self) -> Optional[BaseMessage]:
    if not LANGCHAIN_AVAILABLE:
        return None
    if self.type == MessageType.AI:
        return AIMessage(content=self.content,**self.metadata,additional_kwargs=self.additional_kwargs)
    elif self.type == MessageType.HUMAN:
        return HumanMessage(content=self.content,**self.metadata,additional_kwargs=self.additional_kwargs)
    elif self.type == MessageType.SYSTEM:
        return SystemMessage(content=self.content,**self.metadata,additional_kwargs=self.additional_kwargs)
    elif self.type == MessageType.TOOL:
        return ToolMessage(
            content = self.content,
            tool_call_id = self.tool_call_id or "",
            **self.metadata,
            additional_kwargs=self.additional_kwargs
        )
    return None


class MessageSerializer:

    @staticmethod
    def serialize(message: Any,from_agent: str=None,to_agent: str=None) -> SerializableMessage:
        if isinstance(message, dict):
            if "type" in message and "content" in message:
                return SerializableMessage.from_dict(message)
            return SerializableMessage(
                type=MessageType.SYSTEM,
                content= str(message),
                metadata=message,
                from_agent=from_agent,
                to_agent=to_agent
            )
        if not LANGCHAIN_AVAILABLE:
            return SerializableMessage(
                type=MessageType.SYSTEM,
                content= str(message),
                from_agent=from_agent,
                to_agent=to_agent
            )
        
        msg_type = MessageType.SYSTEM
        content = ""
        metadata = {}
        tool_call_id = None
        tool_name = None
        tool_output = None

        if isinstance(message,AIMessage):
            msg_type = MessageType.AI
            content = message.content
            metadata = getattr(message,'additional_kwargs',{})
        elif isinstance(message,HumanMessage):
            msg_type = MessageType.HUMAN
            content = message.content
            # metadata = getattr(message,'additional_kwargs',{})
        elif isinstance(message,SystemMessage):
            msg_type = MessageType.SYSTEM
            content = message.content
            # metadata = getattr(message,'additional_kwargs',{})
        elif isinstance(message,ToolMessage):
            msg_type = MessageType.TOOL
            content = message.content
            tool_call_id = getattr(message,'tool_call_id',None)
            tool_name = getattr(message,'tool_name',None)
            tool_output = content
            # metadata = getattr(message,'additional_kwargs',{})
        else:
            content = str(message)

        return SerializableMessage(
            type=msg_type,
            content=content,
            metadata=metadata,
            from_agent=from_agent,
            to_agent=to_agent,
            tool_call_id=tool_call_id,
            tool_name=tool_name,
            tool_output=tool_output
        )
    
    @staticmethod
    def serialize_list(messages:List[Any],from_agent:str = None,to_agent: str=None) -> List[Dict[str,Any]]:
        return [MessageSerializer.serialize(msg,from_agent,to_agent).to_dict() for msg in messages]
    @staticmethod
    def deserialize_list(messages: List[Dict[str,Any]])-> List[SerializableMessage]:
        return [SerializableMessage.from_dict(msg) for msg in messages]
    

@dataclass
class ConversationTurn:
    from_agent:str
    to_agent:str
    message:SerializableMessage
    turn_number:int
    timestamp:str = field(default_factory=lambda:datetime.now().isoformat())

class ConversationHistory:

    def __init__(self):
        self._conversations: List[ConversationTurn] = []
        self._agent_queues: Dict[str,List[SerializableMessage]] = []
        self._lock = threading.RLock()

    def add_message(self,
            message:Union[SerializableMessage,Any],
            from_agent:str=None,
            to_agent:str=None)->None:
        
        with self._lock:
            if not isinstance(message,SerializableMessage):
                message = MessageSerializer.serialize(message,from_agent=from_agent,to_agent=to_agent)
            else:
                message.from_agent = from_agent
                message.to_agent = to_agent
        turn = ConversationTurn(
            from_agent=from_agent,
            to_agent=to_agent or "broadcast",
            message=message,
            turn_number=len(self._conversations)+1
        )
        self._conversations.append(turn)
        
        if from_agent not in self._agent_queues:
            self._agent_queues[to_agent] = []
        self._agent_queues[from_agent].append(message)

        if to_agent:
            if to_agent not in self._agent_queues:
                self._agent_queues[to_agent] = []
            recipent_msg = SerializableMessage(
                type=message.type,
                content=message.content,
                timestamp=message.timestamp,
                metadata=message.metadata,
                from_agent=from_agent,
                to_agent=to_agent,
                tool_call_id=message.tool_call_id,
                tool_name=message.tool_name,
                tool_output=message.tool_output
            )
            self._agent_queues[to_agent].append(recipent_msg)


    def get_conversation(
            self,
            agent_a:str = None,
            agent_b:str = None,
            limit:int = None
    ) ->List[ConversationTurn]:
        with self._lock:
            conversations = self._conversations

            if agent_a or agent_b:
                conversations = [
                    turn for turn in conversations
                    if (not agent_a or turn.from_agent == agent_a or turn.to_agent == agent_a)
                    and (not agent_b or turn.from_agent == agent_b or turn.to_agent == agent_b)
                ]
            
            if limit:
                conversations = conversations[-limit:]

            return conversations