import random
from typing import Dict, Optional

"""Simple in-memory ticket store for demo / capstone purposes.

This is intentionally minimal: tickets are stored in a module-level dict and
have the shape:

    TICKETS[ticket_id] = {"message": str, "status": str, "source": "CS"|"NOC"}

This allows the API to create tickets on escalate and return status via
`/ticket/status`. For production, replace with persistent DB or external
ticketing system.
"""

TICKETS: Dict[str, Dict[str, str]] = {}


def _make_id(prefix: str) -> str:
    return f"{prefix}-{random.randint(1000, 9999)}"


def create_ticket(source: str, message: str) -> str:
    """Create a new ticket and return its id.

    source: short prefix like 'CS' or 'NOC'
    """
    tid = _make_id(source.upper())
    TICKETS[tid] = {"message": message, "status": "OPEN", "source": source.upper()}
    return tid


def get_ticket(ticket_id: str) -> Optional[Dict[str, str]]:
    return TICKETS.get(ticket_id)


def get_ticket_status(ticket_id: str) -> Optional[str]:
    t = get_ticket(ticket_id)
    return t["status"] if t else None


def update_ticket_status(ticket_id: str, status: str) -> bool:
    t = get_ticket(ticket_id)
    if not t:
        return False
    t["status"] = status
    return True
