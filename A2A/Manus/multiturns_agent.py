import httpx
from typing import Any, Dict, AsyncIterable, Literal, List, ClassVar
from pydantic import BaseModel
from app.agent.manus import Manus
from app.schema import AgentState
import traceback
import logging
logger = logging.getLogger(__name__)
class ResponseFormat(BaseModel):
    """Respond to the user in this format."""
    status: Literal["input_required", "completed", "error"] = "input_required"
    message: str

class Multiturns_A2AManus(Manus):

    async def invoke(self, query, sessionId) -> str:
        config = {"configurable": {"thread_id": sessionId}}
        response = await self.run_session(sessionId,query)
        return self.get_agent_response(config,response)

    async def stream(self, query: str, sessionId) -> AsyncIterable[Dict[str, Any]]:
        config = {"configurable": {"thread_id": sessionId}}
        yield {
            "is_task_complete": False,
            "require_user_input": False,
            "content":  "processing query"
        }
        try:
            async for response in self.stream_run_session(sessionId,query):
                logger.info(f"Streaming response: {response}")
                yield self.get_agent_response(config,response)
        except Exception as e:
            logger.error(f"Error during streaming: {traceback.format_exc()}")
            yield {
                "is_task_complete": False,
                "require_user_input": True,
                "content": f"Error during streaming:{str(e)}"
            }

    def get_agent_response(self, config, response):
        if "tool 'ask_human_stream' execute result is" in response:
            return {
                "is_task_complete": False,
                "require_user_input": True,
                "content": response
            }
        if "Error" in response:
            return {
                "is_task_complete": False,
                "require_user_input": True,
                "content": response
            }
        if (self.current_step >= self.max_steps and self.state != AgentState.RUNNING) or self.state == AgentState.FINISHED or "Results:" in response:
            return {
                "is_task_complete": True,
                "require_user_input": False,
                "content": response
            }

        return {
            "is_task_complete": False,
            "require_user_input": False,
            "content": response,
        }

    SUPPORTED_CONTENT_TYPES : ClassVar[List[str]] = ["text", "text/plain"]
