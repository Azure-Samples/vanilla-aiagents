# Vanilla AI Agents

Sample package demonstrating how to create a simple agenting application without using any specific framework.

## Features

This project framework provides the following features:

* Multi-agent chat
* Agent routing (including option to look for available tools to decide)
* Agent state management
* Custom stop conditions
* Interactive or unattended user input
* Chat resumability
* Function calling on agents
* Constrained agent routing
* Sub-workflows
* Simple RAG via function calls
* Image input support
* Ability to run pre and post steps via Sequence
* Conversation context "hidden" variables, which are not displayed to the user but agents can read and write to access additional information
* Usage metrics tracking per conversation, plus internal log for debuggability
* Multiple strategies for agent to filter conversation messages (All, last N, top K and Last N, summarize, etc..)
* LLMLingua (`extras` module) support to compress system prompts via strategies
* LLM support for Structured Output
* Remoting support ((`remote` module)), allowing agents to be run on a remote server and accessed elsewhere
  * REST and gRPC channels supported
  * Default implementation to run hosts with agent discovery and registration
* Generated Code execution locally and via ACA Dynamic Sessions
* Streaming support, even over REST or gRPC agents
