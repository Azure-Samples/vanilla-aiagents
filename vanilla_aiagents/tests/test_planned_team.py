from typing import Annotated
import unittest
import os, logging, sys

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from vanilla_aiagents.workflow import Workflow
from vanilla_aiagents.conversation import SummarizeMessagesStrategy
from vanilla_aiagents.agent import Agent
from vanilla_aiagents.planned_team import PlannedTeam
from vanilla_aiagents.llm import AzureOpenAILLM

from dotenv import load_dotenv
load_dotenv(override=True)

class TestPlannedTeam(unittest.TestCase):

    def setUp(self):
        self.llm = AzureOpenAILLM({
            "azure_deployment": os.getenv("AZURE_OPENAI_MODEL"),
            "azure_endpoint": os.getenv("AZURE_OPENAI_ENDPOINT"),
            "api_key": os.getenv("AZURE_OPENAI_KEY"),
            "api_version": os.getenv("AZURE_OPENAI_API_VERSION"),
        })
        
        # Set logging to debug for Agent, User, and Workflow
        logging.basicConfig(level=logging.INFO)
        logging.getLogger("vanilla_aiagents.agent").setLevel(logging.DEBUG)
        logging.getLogger("vanilla_aiagents.planned_team").setLevel(logging.DEBUG)

    def test_fork(self):
        collector = Agent(id="datacollector", llm=self.llm, description="Call this agent to collect data for an insurance claim", system_message = """You are part of an AI process
        Your task is to collect key information for an insurance claim to be processed.
        You need to collect the following information:
        - Policy number
        - Claimant name
        - Date of incident
        - Description of incident
        - Reimbursement amount
        
        Output must be in JSON format:
        {
            "policy_number": "123456",
            "claimant_name": "John Doe",
            "date_of_incident": "2022-01-01",
            "description_of_incident": "Car accident on Maple Avenue",
            "incident_kind": "car accident",
            "reimbursement_amount": 1000
        }
        """)

        
        approver = Agent(id="approver", llm=self.llm, description="Call this agent to approve the claim", system_message = """You are part of an AI process
        Your task is to review the information collected for an insurance claim.
        Approval is subject to the following criteria:
        - If the description refers to a car accident
            - approve the claim if the reimbursement amount is less than 1000 USD
            - reject the claim if the reimbursement amount is 1000 USD or more
        - If the description refers to a house fire
            - approve the claim if the reimbursement amount is less than 5000 USD
            - reject the claim if the reimbursement amount is 5000 USD or more
        """)
        
        responder = Agent(id="responder", llm=self.llm, description="Call this agent to respond to the claim", system_message = """You are part of an AI process
        Your task is to respond to the claimant based on the approval decision.
        If the claim is approved, respond with "Your claim has been approved".
        If the claim is rejected, respond with "Your claim has been rejected". Provide a reason for the rejection.
        """)
        
        flow = PlannedTeam(id="flow", description="", 
                           members=[collector, approver, responder], 
                           llm=self.llm, 
                           stop_callback=lambda msgs: len(msgs) > 6, 
                           fork_conversation=True,
                           fork_strategy=SummarizeMessagesStrategy(self.llm, "Summarize the conversation, focusing on the key points and decisions made."))
        workflow = Workflow(askable=flow)
        workflow.restart()
        
        workflow.run(ticket)
        
        self.assertEqual(len(workflow.conversation.messages), 3, "Expected 3 messages (sys+user+planned) in the original conversation")
        # Expect last message to be a dict with name and content keys
        self.assertIn("name", workflow.conversation.messages[-1], "Expected last message to have a 'name' key")
        self.assertIn("content", workflow.conversation.messages[-1], "Expected last message to have a 'content' key")
        self.assertEqual(workflow.conversation.messages[-1]["name"], "summarizer", "Expected last message to be from the summarizer")
        
    def test_include_tools(self):
        # Telling the agents to set context variables implies calling a pre-defined function call
        first = Agent(id="first", llm=self.llm, description="First agent", system_message = """You are part of an AI process
        Your task is to support the user inquiry by providing the user profile.
        Use a tool to retrieve the user profile.
        """)
        
        @first.register_tool(name="get_user_profile", description="Get the user profile")
        def get_user_profile() -> Annotated[str, "User profile in JSON format"]:
            return "{\"name\": \"John\", \"age\": 30}"

        # Second agent might have its system message extended automatically with the context from the ongoing conversation
        second = Agent(id="second", llm=self.llm, description="Second agent", system_message = """You are part of an AI process
        Your task is to support the user inquiry.
        When the users asks if they are eligible for a discount, use a tool to check the user profile.
        
        When done, include "DONE" in your response.
        """)
        
        @second.register_tool(name="check_discount_eligibility", description="Check if the user is eligible for a discount")
        def check_discount_eligibility(age: Annotated[int, "The user age"]) -> Annotated[str, "Eligibility message"]:
            return "You are eligible for a discount" if age < 25 else "You are not eligible for a discount"
        
        flow = PlannedTeam(id="flow", description="", members=[first, second], llm=self.llm, include_tools_descriptions=True, stop_callback=lambda x: "DONE" in x[-1]["content"])
        workflow = Workflow(askable=flow)
        workflow.restart()
        
        result = workflow.run("Can I have a discount?")
        
        self.assertEqual(result, "callback-stop", "Expected the workflow result to be 'done'")
        self.assertEqual(workflow.conversation.messages[-1]["name"], second.id, "Expected second agent to respond with DONE")
        self.assertIn("not eligible", workflow.conversation.messages[-1]["content"], "Expected result to be 'not eligible'")
        
        # self.assertIn("voice", workflow.conversation.messages[3]["content"], "Expected second agent to recognize context variable CHANNEL")

    def test_plan(self):
        collector = Agent(id="datacollector", llm=self.llm, description="Call this agent to collect data for an insurance claim", system_message = """You are part of an AI process
        Your task is to collect key information for an insurance claim to be processed.
        You need to collect the following information:
        - Policy number
        - Claimant name
        - Date of incident
        - Description of incident
        - Reimbursement amount
        
        Output must be in JSON format:
        {
            "policy_number": "123456",
            "claimant_name": "John Doe",
            "date_of_incident": "2022-01-01",
            "description_of_incident": "Car accident on Maple Avenue",
            "incident_kind": "car accident",
            "reimbursement_amount": 1000
        }
        """)

        
        approver = Agent(id="approver", llm=self.llm, description="Call this agent to approve the claim", system_message = """You are part of an AI process
        Your task is to review the information collected for an insurance claim.
        Approval is subject to the following criteria:
        - If the description refers to a car accident
            - approve the claim if the reimbursement amount is less than 1000 USD
            - reject the claim if the reimbursement amount is 1000 USD or more
        - If the description refers to a house fire
            - approve the claim if the reimbursement amount is less than 5000 USD
            - reject the claim if the reimbursement amount is 5000 USD or more
        """)
        
        responder = Agent(id="responder", llm=self.llm, description="Call this agent to respond to the claim", system_message = """You are part of an AI process
        Your task is to respond to the claimant based on the approval decision.
        If the claim is approved, respond with "Your claim has been approved".
        If the claim is rejected, respond with "Your claim has been rejected". Provide a reason for the rejection.
        """)
        
        flow = PlannedTeam(id="flow", description="", members=[collector, approver, responder], llm=self.llm, stop_callback=lambda msgs: len(msgs) > 6)
        workflow = Workflow(askable=flow)
        workflow.restart()
        
        workflow.run(ticket)
        
        # Should be as follows:
        # 0. system message from the workflow
        # 1. user input
        # 2. data collector input
        # 3. data collector response
        # 4. approver input
        # 5. approver response
        # 6. responder input
        # 7. responder response
        self.assertEqual(len(workflow.conversation.messages), 8, "Expected 8 messages in the conversation")
        
        self.assertEqual(workflow.conversation.messages[3]["name"], "datacollector", "Expected data collector to respond first")
        self.assertIn("car accident", workflow.conversation.messages[3]["content"].lower(), "Expected data collector to respond with incident description for car accident")
        self.assertIn("1000", workflow.conversation.messages[3]["content"], "Expected data collector to respond with reimbursement amount of 1000")
        
        self.assertEqual(workflow.conversation.messages[5]["name"], "approver", "Expected approver to respond second")
        self.assertIn("reject", workflow.conversation.messages[5]["content"], "Expected approver to reject the claim")
        
        self.assertEqual(workflow.conversation.messages[7]["name"], "responder", "Expected responder to respond last")
        self.assertIn("rejected", workflow.conversation.messages[7]["content"], "Expected responder to respond with claim rejection message")

ticket= """
From: Alice Thompson <a_thompson@foo.com>
To: Contoso Insurance Team <report@contoso-insurancec.com>
Subject: URGENT: Car Accident Claim - Immediate Assistance Required

Dear Contoso Insurance Team,

I hope this email finds you well. I am writing to you with a heavy heart and a great deal of stress regarding an unfortunate incident that occurred earlier today. I was involved in a car accident and I am seeking immediate assistance to file a claim and get the support I need during this challenging time.

Here's what happened: I was driving home from work, heading south on Maple Avenue, when out of nowhere, another vehicle came speeding through a red light at the intersection of Maple and Oak Street. I had no time to react, and the other car crashed into the passenger side of my vehicle with considerable force. The impact was severe, and both cars were significantly damaged. My car, a 2018 Toyota Camry, has extensive damage to the passenger side, and I believe it may not be drivable at this point.

Thankfully, I did not sustain any major injuries, but I am feeling quite shaken up and have some minor bruises. The other driver appeared to be unharmed as well, but their car, a silver Honda Civic, was also badly damaged. We exchanged contact and insurance information at the scene, and I made sure to take photos of the damage to both vehicles for documentation purposes.

The accident was promptly reported to the local authorities, and a police report was filed. I have attached a copy of the police report, along with the photos I took, for your reference. Additionally, I have provided my insurance policy number and other relevant details below to expedite the process.

Policy Number: 2021-123456789
Date of Accident: Monday, August 23, 2022
Location: Intersection of Maple Avenue and Oak Street
Vehicle Involved: 2018 Toyota Camry (License Plate: AAA-1234)
Other Party Involved: Silver Honda Civic (License Plate: ZZZ-5678)

I am deeply concerned about the repair costs ($ 1000) and the potential need for a rental car while my vehicle is being repaired. I would greatly appreciate it if you could guide me through the next steps and let me know what information or documentation you require from my end to process the claim efficiently.

This is a very distressing situation for me, and I am relying on your prompt assistance and expertise to help me navigate this process. Please let me know if there are any forms I need to fill out or additional information I need to provide.

Thank you in advance for your understanding and support during this difficult time. I look forward to hearing from you soon and hope for a swift resolution to my claim.

Warm regards,

Alice Thompson
"""

if __name__ == '__main__':
    unittest.main()