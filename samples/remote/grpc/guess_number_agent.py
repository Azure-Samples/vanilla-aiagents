from typing import Annotated
import os
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.llm import AzureOpenAILLM

llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })

guess_number = Agent(id="agent", llm=llm, description="Call this agent to play guess the number game with the use", system_message = """You are an AI assistant
        Your task is to play a game with the user.
        You first generate a random number between 1 and 100. Then save it as a conversation variable named "number".
        The user will try to guess the number.
        If the user's guess is too high, respond with "Too high".
        If the user's guess is too low, respond with "Too low".
        """)
        
@guess_number.register_tool(description="Generate a random number")
def random() -> Annotated[str, "A random number"]:
    return str(random.randint(1, 100))