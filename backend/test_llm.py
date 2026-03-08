import asyncio
import os
import sys

# add parent dir so app can be imported
sys.path.append('/home/alexandre/Dev/Croo Digital Experience/croo-digital-experience-v.2.0/backend')

from app.agents.bob_chat_agent import BobChatAgent
from app.config import settings

def main():
    agent = BobChatAgent()
    session = agent.get_or_create_session(
        session_id="test_session_1", 
        user_id="foo", 
        tenant_id="bar", 
        user_email="test@croo.com"
    )
    resp, actions = agent.chat("test_session_1", "I want to do my CRM training")
    print("Response:", resp)
    print("Actions:", actions)

    resp, actions = agent.chat("test_session_1", "start the CRM training")
    print("Response:", resp)
    print("Actions:", actions)

if __name__ == "__main__":
    main()
