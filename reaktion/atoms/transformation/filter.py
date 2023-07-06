import asyncio
from typing import List
from reaktion.atoms.combination.base import CombinationAtom
from reaktion.events import EventType, OutEvent
import logging

logger = logging.getLogger(__name__)


class FilterAtom(CombinationAtom):
    complete: List[bool] = [False, False]

    async def run(self):
        try:
            while True:
                event = await self.get()

                if event.type == EventType.ERROR:
                    for index, stream in enumerate(self.node.outstream):
                        await self.transport.put(
                            OutEvent(
                                handle=f"return_{index}",
                                type=EventType.ERROR,
                                value=event.value,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                    break

                if event.type == EventType.NEXT:
                    value = event.value[0]
                    print(event.value)
                    real_value = value["value"]
                    index = value["use"]
                    print(real_value, index)
                    await self.transport.put(
                        OutEvent(
                            handle=f"return_{index}",
                            type=EventType.NEXT,
                            value=(real_value,),
                            source=self.node.id,
                            caused_by=[event.current_t],
                        )
                    )

                if event.type == EventType.COMPLETE:
                    for index, stream in enumerate(self.node.outstream):
                        await self.transport.put(
                            OutEvent(
                                handle=f"return_{index}",
                                type=EventType.COMPLETE,
                                source=self.node.id,
                                caused_by=[event.current_t],
                            )
                        )
                    break

        except asyncio.CancelledError as e:
            logger.warning(f"Atom {self.node} is getting cancelled")
            raise e

        except Exception as e:
            logger.exception(f"Atom {self.node} excepted")
            raise e
