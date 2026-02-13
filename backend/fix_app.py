"""QuickFIX Initiator Application for the trading desk.

Manages the FIX session lifecycle and handles incoming execution reports.
Publishes session status and execution reports to Redis so the frontend
(or any subscriber) can react in real time.
"""

import json
import logging

import quickfix as fix

from shared.redis_client import get_redis_connection
from shared.constants import REDIS_KEY_EXECUTION_REPORTS, REDIS_KEY_FIX_STATUS
from backend.message_parser import fix_to_dict

logger = logging.getLogger("fix_app")


class FixApplication(fix.Application):

    def __init__(self):
        super().__init__()
        self.session_id = None
        self.is_logged_on = False
        self._redis = get_redis_connection()

    # ------------------------------------------------------------------
    # Session lifecycle
    # ------------------------------------------------------------------

    def onCreate(self, session_id):
        self.session_id = session_id
        logger.info(f"FIX session created: {session_id}")

    def onLogon(self, session_id):
        self.session_id = session_id
        self.is_logged_on = True
        logger.info(f"FIX session LOGGED ON: {session_id}")
        if self._redis:
            self._redis.set(REDIS_KEY_FIX_STATUS, "LOGGED_ON")

    def onLogout(self, session_id):
        self.is_logged_on = False
        logger.warning(f"FIX session LOGGED OUT: {session_id}")
        if self._redis:
            self._redis.set(REDIS_KEY_FIX_STATUS, "LOGGED_OFF")

    # ------------------------------------------------------------------
    # Admin messages (Logon, Heartbeat, etc.)
    # ------------------------------------------------------------------

    def toAdmin(self, message, session_id):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)
        if msg_type.getValue() == fix.MsgType_Logon:
            logger.debug("Sending Logon message")
            # To inject credentials:
            # message.setField(fix.Username("user"))
            # message.setField(fix.Password("pass"))

    def fromAdmin(self, message, session_id):
        logger.debug(f"Admin IN: {message}")

    # ------------------------------------------------------------------
    # Application messages (NewOrderSingle, ExecutionReport, etc.)
    # ------------------------------------------------------------------

    def toApp(self, message, session_id):
        logger.info(f"App OUT: {message}")

    def fromApp(self, message, session_id):
        msg_type = fix.MsgType()
        message.getHeader().getField(msg_type)

        if msg_type.getValue() == "8":  # ExecutionReport
            self._handle_execution_report(message)
        else:
            logger.info(f"App IN (type={msg_type.getValue()}): {message}")

    # ------------------------------------------------------------------
    # Internal handlers
    # ------------------------------------------------------------------

    def _handle_execution_report(self, message):
        report = fix_to_dict(message)
        report["_type"] = "ExecutionReport"
        logger.info(f"Execution Report: {report}")
        if self._redis:
            self._redis.lpush(REDIS_KEY_EXECUTION_REPORTS, json.dumps(report))

    # ------------------------------------------------------------------
    # Public API (called by engine.py)
    # ------------------------------------------------------------------

    def send_order(self, fix_message):
        """Send a FIX message through the active session. Returns True on success."""
        if not self.is_logged_on or not self.session_id:
            logger.warning("Cannot send — FIX session not logged on")
            return False
        try:
            fix.Session.sendToTarget(fix_message, self.session_id)
            return True
        except fix.SessionNotFound:
            logger.error("FIX session not found when trying to send")
            return False
