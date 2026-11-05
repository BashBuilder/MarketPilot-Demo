"""Tests for run-scoped context propagation into JSON logs."""

import io
import json
import logging

from app.core.logging import JsonFormatter, bind_run_context, run_id_var


def _capture(logger_name: str) -> tuple[logging.Logger, io.StringIO]:
    logger = logging.getLogger(logger_name)
    logger.setLevel(logging.INFO)
    logger.propagate = False
    stream = io.StringIO()
    handler = logging.StreamHandler(stream)
    handler.setFormatter(JsonFormatter())
    logger.addHandler(handler)
    return logger, stream


def test_run_id_appears_in_log_output() -> None:
    logger, stream = _capture("marketpilot.tests.run_id")
    try:
        with bind_run_context(
            run_id="run-123",
            campaign_id="campaign-9",
            agent="brief",
            step="3",
        ):
            logger.info("brief completed")
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    payload = json.loads(stream.getvalue())

    assert payload["run_id"] == "run-123"
    assert payload["campaign_id"] == "campaign-9"
    assert payload["agent"] == "brief"
    assert payload["step"] == "3"
    assert payload["message"] == "brief completed"
    assert payload["level"] == "INFO"


def test_run_context_is_cleared_after_block() -> None:
    logger, stream = _capture("marketpilot.tests.cleanup")
    try:
        with bind_run_context(run_id="run-456"):
            assert run_id_var.get() == "run-456"
        logger.info("after run")
    finally:
        for handler in list(logger.handlers):
            logger.removeHandler(handler)

    payload = json.loads(stream.getvalue())

    assert run_id_var.get() is None
    assert "run_id" not in payload
