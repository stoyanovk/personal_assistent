from langgraph.checkpoint.memory import InMemorySaver
from langchain_openai import ChatOpenAI
from langchain.agents import create_agent
from langchain_core.messages import (
    HumanMessage,
)
from app.agent.prompt import build_system_prompt
from app.agent.schema import ParsedItem
from app.config import settings

model = ChatOpenAI(model="gpt-5.4-mini", api_key=settings.openai_api_key)

memory = InMemorySaver()

agent = create_agent(
    model=model,
    system_prompt=build_system_prompt(),
    response_format=ParsedItem,
    checkpointer=memory,
)


def get_thread_id(user_id: int) -> str:
    return f"""thread_id:{user_id}"""


def clear_intend_state(user_id: int) -> None:
    memory.delete_thread(get_thread_id(user_id))


async def get_intent(message: str, user_id: int) -> ParsedItem:
    result = await agent.ainvoke(
        {"messages": [HumanMessage(message)]},
        config={"configurable": {"thread_id": get_thread_id(user_id)}},
    )
    return result["structured_response"]
