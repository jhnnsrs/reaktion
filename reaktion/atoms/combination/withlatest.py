import asyncio
from typing import List, Optional, Tuple
import uuid
from reaktion.atoms.helpers import index_for_handle
from rekuest.api.schema import AssignationLogLevel
from rekuest.messages import Assignation
from reaktion.atoms.combination.base import CombinationAtom
from reaktion.events import EventType, OutEvent, Returns
import logging
import functools

logger = logging.getLogger(__name__)


class WithLatestAtom(CombinationAtom):
    state: List[Optional[List[Returns]]] = [None, None]
    complete: List[bool] = [None, None]

    async def run(self):
        self.state = list(map(lambda x: None, self.node.instream))
        self.complete = list(map(lambda x: False, self.node.instream))

        initial_fire = True  # Will be set to False after the first event has been fired (first all none )
        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    await self.transport.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            value=event.value,
                            source=self.node.id,
                        )
                    )
                    break

                streamIndex = index_for_handle(event.handle)

                if event.type == EventType.COMPLETE:
                    self.complete[streamIndex] = True

                    if streamIndex == 0:
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.COMPLETE,
                                source=self.node.id,
                            )
                        )
                        break

                if event.type == EventType.NEXT:
                    self.state[streamIndex] = event.value

                    if self.state.count(None) == 0 and (
                        streamIndex == 0 or initial_fire
                    ):
                        initial_fire = False
                        await self.transport.put(
                            OutEvent(
                                handle="return_0",
                                type=EventType.NEXT,
                                value=functools.reduce(lambda a, b: a + b, self.state),
                                source=self.node.id,
                            )
                        )

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception as e:
            logger.exception(f"Atom {self.node} excepted")
