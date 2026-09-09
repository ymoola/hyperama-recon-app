import asyncio
import logging
import math
import random
import threading
import time
from collections import deque
from dataclasses import dataclass

import httpx
import streamlit as st
from google.genai import errors

from config.settings import get_gemini_limits


LOGGER = logging.getLogger(__name__)
WINDOW_SECONDS = 60
MAX_CONCURRENCY = 12
MAX_ATTEMPTS = 6
INITIAL_TOKEN_ESTIMATE = 100_000
RETRYABLE_CODES = {408, 429, 500, 502, 503, 504}


@dataclass
class Reservation:
    timestamp: float
    tokens: int


class GeminiQuotaCoordinator:
    def __init__(
        self, rpm, tpm, headroom=0.8, max_concurrency=MAX_CONCURRENCY,
        clock=time.monotonic,
    ):
        if rpm <= 0 or tpm <= 0 or max_concurrency <= 0 or not 0 < headroom <= 1:
            raise ValueError("Gemini limits and headroom must be positive.")
        self.rpm = max(1, math.floor(rpm * headroom))
        self.tpm = max(1, math.floor(tpm * headroom))
        self.max_concurrency = max_concurrency
        self.clock = clock
        self._lock = threading.Lock()
        self._reservations = deque()
        self._observed_tokens = deque(maxlen=20)
        self._active = 0

    def _prune(self, now):
        while self._reservations and now - self._reservations[0].timestamp >= WINDOW_SECONDS:
            self._reservations.popleft()

    def token_estimate(self):
        with self._lock:
            if not self._observed_tokens:
                return min(INITIAL_TOKEN_ESTIMATE, self.tpm)
            estimate = math.ceil(max(self._observed_tokens) * 1.25)
            return min(self.tpm, max(10_000, estimate))

    def try_reserve(self, tokens=None):
        with self._lock:
            now = self.clock()
            self._prune(now)
            tokens = min(self.tpm, max(1, tokens or self.token_estimate_unlocked()))
            token_total = sum(item.tokens for item in self._reservations)
            if (
                self._active < self.max_concurrency
                and len(self._reservations) < self.rpm
                and token_total + tokens <= self.tpm
            ):
                reservation = Reservation(now, tokens)
                self._reservations.append(reservation)
                self._active += 1
                return reservation, 0

            if self._active >= self.max_concurrency:
                return None, 0.1
            wait = WINDOW_SECONDS - (now - self._reservations[0].timestamp)
            return None, min(0.5, max(0.05, wait))

    def token_estimate_unlocked(self):
        if not self._observed_tokens:
            return min(INITIAL_TOKEN_ESTIMATE, self.tpm)
        return min(
            self.tpm,
            max(10_000, math.ceil(max(self._observed_tokens) * 1.25)),
        )

    def release(self, reservation, actual_tokens=None):
        with self._lock:
            if actual_tokens and actual_tokens > 0:
                reservation.tokens = actual_tokens
                self._observed_tokens.append(actual_tokens)
            self._active -= 1

    def wait_for_reservation(self, tokens=None):
        while True:
            reservation, wait = self.try_reserve(tokens)
            if reservation:
                return reservation
            time.sleep(wait)

    async def wait_for_reservation_async(self, tokens=None):
        while True:
            reservation, wait = self.try_reserve(tokens)
            if reservation:
                return reservation
            await asyncio.sleep(wait)


@st.cache_resource
def get_gemini_coordinator():
    rpm, tpm, headroom = get_gemini_limits()
    coordinator = GeminiQuotaCoordinator(rpm, tpm, headroom)
    LOGGER.info(
        "Gemini limits active: %d RPM, %d input TPM, %d concurrent",
        coordinator.rpm,
        coordinator.tpm,
        MAX_CONCURRENCY,
    )
    return coordinator


def response_tokens(response):
    usage = getattr(response, "usage_metadata", None)
    return getattr(usage, "prompt_token_count", None)


def is_retryable(error):
    return (
        isinstance(error, errors.APIError) and error.code in RETRYABLE_CODES
    ) or isinstance(error, (httpx.TimeoutException, httpx.ConnectError, TimeoutError))


def retry_delay(error, attempt):
    headers = getattr(getattr(error, "response", None), "headers", {}) or {}
    try:
        retry_after = float(headers.get("retry-after"))
    except (TypeError, ValueError):
        retry_after = 2 ** (attempt - 1) + random.random()
    return min(60, max(0, retry_after))
