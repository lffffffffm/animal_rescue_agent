from app.llm.chat_model import ChatModel

_default_llm = None


def get_llm():
    global _default_llm
    if _default_llm is None:
        _default_llm = ChatModel()
    return _default_llm
