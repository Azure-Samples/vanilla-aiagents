import argparse
import logging
from dotenv import load_dotenv

from .actors import InputWorkflowEvent, WorkflowActor, WorkflowActorInterface
import os
import uvicorn
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from dapr.ext.fastapi import DaprActor, DaprApp
from dapr.actor import ActorProxy, ActorId
from cloudevents.http import from_http


load_dotenv(override=True)
# Configure logging
logger = logging.getLogger(__name__)
PUBSUB_NAME = os.getenv("PUBSUB_NAME", "workflow")
TOPIC_NAME = os.getenv("TOPIC_NAME", "events")


def main():
    parser = argparse.ArgumentParser(description="Run the Dapr Actor host")
    parser.add_argument(
        "--host", type=str, default="0.0.0.0", help="Host to run the server on."
    )
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run the server on."
    )
    parser.add_argument("--log-level", default="INFO", help="Set the logging level")

    args = parser.parse_args()

    log_level = getattr(logging, args.log_level.upper(), logging.INFO)
    logging.basicConfig(level=log_level)
    logger.setLevel(log_level)

    actor: DaprActor = None

    # Register actor when fastapi starts up
    @asynccontextmanager
    async def lifespan(app: FastAPI):
        logger.info("~~ actor startup")
        await actor.register_actor(WorkflowActor)
        yield

    # Create fastapi and register dapr, and actors
    app = FastAPI(title="Vanilla AI Agent Dapr Actors host", lifespan=lifespan)
    actor = DaprActor(app)
    dapr_app = DaprApp(app)

    @dapr_app.subscribe(
        pubsub=PUBSUB_NAME,
        topic=TOPIC_NAME,
    )
    async def handle_workflow_input(req: Request):
        try:

            # Read fastapi request body as text
            body = await req.body()
            logger.info(f"Received workflow input: {body}")

            # Parse the body as a CloudEvent
            event = from_http(data=body, headers=req.headers)

            data = InputWorkflowEvent.model_validate(event.data)
            proxy: WorkflowActorInterface = ActorProxy.create(
                "WorkflowActor", ActorId(data.id), WorkflowActorInterface
            )
            await proxy.run(data.input)

            return {"status": "SUCCESS"}
        except Exception as e:
            logger.error(f"Error handling workflow input: {e}")
            return {"status": "DROP", "message": str(e)}

    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
