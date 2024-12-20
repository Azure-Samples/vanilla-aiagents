import os, sys, signal

sys.path.append(os.path.abspath(os.path.join('../../../vanilla_aiagents')))
from dotenv import load_dotenv
load_dotenv(override=True)


from vanilla_aiagents.askable import Askable
from vanilla_aiagents.remote.remote import RESTHost

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
    host = RESTHost(askables=find_askables(), host=os.getenv("HOST", "0.0.0.0"), port=int(os.getenv("PORT", 8000)))
    
    # Handle SIGINT
    def signal_handler(*args):
        print("Stopping server...")
        host.stop()
        sys.exit(0)
    signal.signal(signal.SIGINT, signal_handler)
    
    host.start()
