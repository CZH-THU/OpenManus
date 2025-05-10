from abc import ABC, abstractmethod
from typing import AsyncGenerator, Optional

from pydantic import Field

from app.agent.base import BaseAgent
from app.llm import LLM
from app.schema import AgentState, Memory


class ReActAgent(BaseAgent, ABC):
    name: str
    description: Optional[str] = None

    system_prompt: Optional[str] = None
    next_step_prompt: Optional[str] = None

    llm: Optional[LLM] = Field(default_factory=LLM)
    memory: Memory = Field(default_factory=Memory)
    state: AgentState = AgentState.IDLE

    max_steps: int = 10
    current_step: int = 0

    @abstractmethod
    async def think(self) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def act(self) -> str:
        """Execute decided actions"""

    @abstractmethod
    async def stream_think(self) -> bool:
        """Process current state and decide next action"""
    @abstractmethod
    async def think_session(self,sessionId:str) -> bool:
        """Process current state and decide next action"""
    @abstractmethod
    async def stream_think_session(self,sessionId:str) -> bool:
        """Process current state and decide next action"""

    @abstractmethod
    async def stream_act(self) -> str:
        """Execute decided actions"""

    @abstractmethod
    async def act_session(self,sessionId:str) -> str:
        """Execute decided actions"""
    @abstractmethod
    async def stream_act_session(self,sessionId:str) -> str:
        """Execute decided actions"""

    async def step(self) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think()
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act()
    async def step_session(self,sessionId:str) -> str:
        """Execute a single step: think and act."""
        should_act = await self.think_session(sessionId)
        if not should_act:
            return "Thinking complete - no action needed"
        return await self.act_session(sessionId)

    async def stream_step(self) -> AsyncGenerator[str, None]:
        """Execute a single step: think and act."""
        should_act = False
        async for think_content in self.stream_think():
            if isinstance(think_content, bool):
                should_act = think_content
                break
            yield think_content
        if not should_act:
            yield "Thinking complete - no action needed"
            return
        async for act in self.stream_act():
            yield act

    async def stream_step_session(self,sessionId:str) -> AsyncGenerator[str, None]:
        """Execute a single step: think and act."""
        should_act = False
        async for think_content in self.stream_think_session(sessionId):
            if isinstance(think_content, bool):
                should_act = think_content
                break
            yield think_content
        if not should_act:
            yield "Thinking complete - no action needed"
            return
        async for act in self.stream_act_session(sessionId):
            yield act
