from app.orchestrator.agents.base import AgentContext
from app.orchestrator.agents.drive import DriveAgent
from app.orchestrator.agents.gcal import GCalAgent
from app.orchestrator.agents.gmail import GmailAgent

AGENTS = {"gmail": GmailAgent, "gcal": GCalAgent, "drive": DriveAgent}

__all__ = ["AgentContext", "GmailAgent", "GCalAgent", "DriveAgent", "AGENTS"]
