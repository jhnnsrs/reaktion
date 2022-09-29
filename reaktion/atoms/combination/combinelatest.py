import asyncio
from typing import List, Tuple
import uuid
from rekuest.api.schema import AssignationLogLevel
from rekuest.messages import Assignation
from reaktion.atoms.combination.base import CombinationAtom
from reaktion.events import EventType, OutEvent, Returns
import logging

logger = logging.getLogger(__name__)


class CombineLatestAtom(CombinationAtom):
    state: List[Returns] = [None, None]
    complete: Tuple[bool, bool] = (False, False)

    async def run(self):
        try:
            while True:
                event = await self.private_queue.get()

                if event.type == EventType.ERROR:
                    await self.event_queue.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.ERROR,
                            value=event.value,
                            source=self.node.id,
                        )
                    )
                    break

                if event.handle == "arg_0":
                    if event.type == EventType.COMPLETE:
                        self.complete = (True, self.complete[1])
                    else:
                        self.state = (event, self.state[1])

                if event.handle == "arg_1":
                    if event.type == EventType.COMPLETE:
                        self.complete = (self.complete[0], True)
                    else:
                        self.state = (self.state[0], event)

                if self.complete == (True, True):
                    if self.alog:
                        await self.alog(
                            self.node.id,
                            AssignationLogLevel.INFO,
                            "ZipAtom: Complete",
                        )
                    await self.event_queue.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.COMPLETE,
                            source=self.node.id,
                        )
                    )
                    break  # Everything left of us is done, so we can shut down as well

                if self.state[0] is not None and self.state[1] is not None:

                    await self.event_queue.put(
                        OutEvent(
                            handle="return_0",
                            type=EventType.NEXT,
                            value=self.state[0].value + self.state[1].value,
                            source=self.node.id,
                        )
                    )
                    self.state = (None, None)

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception as e:
            logger.exception(f"Atom {self.node} excepted")
