import sys
import os
from dotenv import load_dotenv

load_dotenv(override=True)

sys.path.append(os.path.abspath(os.path.join("../../../vanilla_aiagents")))

from vanilla_aiagents.remote.dapr.run_actors import main

if __name__ == "__main__":
    main()
