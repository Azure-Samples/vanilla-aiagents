# Remote agents

The framework supports remote agents. This allows you to run agents on a remote host and interact with them from another one, fostering a more distributed architecture and enabling agent reuse across different applications and `Team`.

The `remote` submodule provides a default implementation to run hosts with agent discovery and registration. It supports REST and gRPC channels. Then, you can simply swap any `Agent` with a `RemoteAgent` and interact with it as if it were local.

## Comparing to Actors

Vanilla also offers a Virtual Actor pattern implementation via Dapr. This allows for the hosting of `Workflow` as Dapr Actors, enabling event sourcing and decoupled communication between workflows.

The key difference between is standard remoting simply offers **stateless** agents, while Dapr Actors offer **stateful** workflows. This means that Dapr Actors can maintain state across multiple interactions, while remote agents are simply APIs that are called and return a result.

See the [Actors documentation](actors.md) for more information.

## Example

```python
# agent_entry.py

from vanilla_aiagents.agent import Agent

agent = Agent(id="agent", description="A remote agent", system_message="You are a remote agent.")
```

```dockerfile
# Dockerfile

FROM python:3.12-slim

# Do all the copying and installing
# ...

# Expose the application port (must match the one specified below)
EXPOSE 80

# This is the entrypoint, Vanilla will automatically look for "_entry.py" files and expose them as agents
CMD ["python", "-m", "vanilla_aiagents.remote.run_host", "--source-dir", ".", "--type", "rest", "--host", "0.0.0.0", "--port", "80"]
```

```python
# client.py

from vanilla_aiagents.remote.remote import RemoteAskable, RESTConnection

# Create a remote connection with the given protocol and host
# NOTE: Make sure to set the HOST_URL environment variable to the host URL
remote_connection = RESTConnection(url=os.getenv("HOST_URL"))

# ID here must match the agent ID in the remote host to use
# NOTE: remote must be running and reachable at this point, since the RemoteAskable will try to connect to it
remote = RemoteAskable(id="agent", connection=remote_connection)

team = Team(id="team", description="Contoso team", members=[remote], llm=llm)
```
