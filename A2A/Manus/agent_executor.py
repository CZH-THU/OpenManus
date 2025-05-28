import logging

from a2a.server.agent_execution import AgentExecutor, RequestContext
from a2a.server.events import Event, EventQueue
from a2a.server.tasks import TaskUpdater
from a2a.types import (
    InternalError,
    Part,
    Task,
    TaskState,
    TextPart,
    UnsupportedOperationError,
    InvalidParamsError
)
from a2a.utils import (
    completed_task,
    new_artifact,
    new_agent_text_message,
    new_task,
)

from A2A.Manus.agent import A2AManus
from a2a.utils.errors import ServerError
from typing import Callable, Awaitable

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class ManusExecutor(AgentExecutor):
    """Currency Conversion AgentExecutor Example."""

    def __init__(self,agent_factory:Callable[[],Awaitable[A2AManus]]):
        self.agent_factory = agent_factory

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        try:
            self.agent = await self.agent_factory()
            result = await self.agent.invoke(query, context.context_id)
            print(f'Final Result ===> {result}')
        except Exception as e:
            print('Error invoking agent: %s', e)
            raise ServerError(
                error=ValueError(f'Error invoking agent: {e}')
            ) from e
        parts = [
            Part(
                root=TextPart(
                    text=result["content"] if result["content"]  else 'failed to generate response'
                ),
            )
        ]
        event_queue.enqueue_event(
            completed_task(
                context.task_id,
                context.context_id,
                [new_artifact(parts, f'task_{context.task_id}')],
                [context.message],
            )
        )
    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())

class StreamManusExecutor(AgentExecutor):
    def __init__(self,agent: A2AManus):
        self.agent = agent

    async def execute(
        self,
        context: RequestContext,
        event_queue: EventQueue,
    ) -> None:
        error = self._validate_request(context)
        if error:
            raise ServerError(error=InvalidParamsError())

        query = context.get_user_input()
        task = context.current_task
        if not task:
            task = new_task(context.message)
            event_queue.enqueue_event(task)
        updater = TaskUpdater(event_queue, task.id, task.contextId)
        try:
            async for item in self.agent.stream(query, task.contextId):
                is_task_complete = item['is_task_complete']
                require_user_input = item['require_user_input']

                if not is_task_complete and not require_user_input:
                    updater.update_status(
                        TaskState.working,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                    )
                elif require_user_input:
                    updater.update_status(
                        TaskState.input_required,
                        new_agent_text_message(
                            item['content'],
                            task.contextId,
                            task.id,
                        ),
                        final=True,
                    )
                    break
                else:
                    updater.add_artifact(
                        [Part(root=TextPart(text=item['content']))],
                        name='conversion_result',
                    )
                    updater.complete()
                    break

        except Exception as e:
            logger.error(f'An error occurred while streaming the response: {e}')
            raise ServerError(error=InternalError()) from e

    def _validate_request(self, context: RequestContext) -> bool:
        return False

    async def cancel(
        self, request: RequestContext, event_queue: EventQueue
    ) -> Task | None:
        raise ServerError(error=UnsupportedOperationError())
