# LLM

The `LLM` class represents a language model used by agents and teams to generate responses. This an abstract base class for all language models platforms.

## Usage

```python
from vanilla_aiagents.llm import AzureOpenAILLM

llm = AzureOpenAILLM({
    "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
    "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
    "api_key": os.getenv("AZURE_OPENAI_KEY"),
    "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
})
```
