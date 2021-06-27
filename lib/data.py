import dataclasses


@dataclasses.dataclass
class BotData:
    admin_chat: str = ''
    # chats: List[str] = dataclasses.field(default_factory=list)
    # chat_names: Dict[str, str] = dataclasses.field(default_factory=dict)
    # latest_messages: Dict[str, int] = dataclasses.field(default_factory=dict)
    # saved_messages: Dict[str, int] = dataclasses.field(default_factory=dict)


@dataclasses.dataclass
class CacheFile:
    admin_chat: str
    chat_id: str
    message_id: str
    parent: str
    filename: str
    payload: bytes