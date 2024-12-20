# Sequence

The `Sequence` class represents a sequence of steps that need to be executed in order. This can be used to ensure that specific steps are always performed in a specific order, mixing classic code with LLM invocations.

## Usage

```python
from vanilla_aiagents.sequence import Sequence

step1 = SetChannelAskable()
step2 = Team(id="...", description="...")
step3 = FormatOutputAskable()

sequence = Sequence(id="sequence1", steps=[step1, step2, step3])
```
