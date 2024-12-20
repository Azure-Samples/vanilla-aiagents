import os, sys

sys.path.append(os.path.abspath(os.path.join('../../../vanilla_aiagents')))
from dotenv import load_dotenv
load_dotenv(override=True)


from vanilla_aiagents.askable import Askable
from vanilla_aiagents.remote.grpc import GRPCHost

# Find all askables in the current directory, and import them as modules
import os
import importlib.util
import logging

logger = logging.getLogger(__name__)

# Find all askables in the current directory, and import them as modules
import os
import importlib.util
import logging

logger = logging.getLogger(__name__)

def find_askables():
    askables = []
    for filename in os.listdir(os.path.dirname(os.path.realpath(__file__))):
        if filename.endswith("_agent.py") and filename != "main.py":
            module_name = filename[:-3]
            spec = importlib.util.spec_from_file_location(module_name, filename)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            for name in dir(module):
                obj = getattr(module, name)
                if isinstance(obj, Askable):
                    askables.append(obj)
    return askables

if __name__ == "__main__":
    host = GRPCHost(askables=find_askables(), host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))
    host.start()
