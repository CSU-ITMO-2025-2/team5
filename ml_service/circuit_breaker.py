import time
import asyncio
from typing import Callable, Any, TypeVar, Coroutine, Optional, Tuple
import httpx

T = TypeVar("T")


class CircuitBreaker:
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (Exception,),
        name: str = "CircuitBreaker",
    ):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.name = name

        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self._lock = asyncio.Lock()
        self._success_count = 0
        self._half_open_max_successes = 3

    async def call(
        self, func: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs
    ) -> T:
        async with self._lock:
            if self.state == "OPEN":
                if time.time() - self.last_failure_time > self.recovery_timeout:
                    self.state = "HALF_OPEN"
                    self.failure_count = 0
                    self._success_count = 0
                    self._log(f"Transitioned to HALF_OPEN")
                else:
                    raise Exception(
                        f"Circuit breaker '{self.name}' is OPEN - service unavailable"
                    )

        try:
            result = await func(*args, **kwargs)
            await self._on_success()
            return result
        except self.expected_exception as e:
            await self._on_failure()
            raise e

    async def _on_success(self) -> None:
        """Handle successful function execution."""
        async with self._lock:
            if self.state == "HALF_OPEN":
                self._success_count += 1
                self._log(
                    f"Success #{self._success_count}/{self._half_open_max_successes} in HALF_OPEN"
                )

                if self._success_count >= self._half_open_max_successes:
                    self.reset()
                    self._log("Successfully recovered, reset to CLOSED")
            elif self.state == "CLOSED":
                # Reset failure count on success in CLOSED state
                if self.failure_count > 0:
                    self.failure_count = 0
                    self._log("Reset failure count on success")

    async def _on_failure(self) -> None:
        """Handle function execution failure."""
        async with self._lock:
            self.failure_count += 1
            self.last_failure_time = time.time()
            self._log(f"Failure #{self.failure_count}/{self.failure_threshold}")

            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                self._log("Transitioned to OPEN due to failure threshold")

    def reset(self) -> None:
        """Reset circuit breaker to CLOSED state."""
        self.failure_count = 0
        self._success_count = 0
        self.state = "CLOSED"
        self._log("Reset to CLOSED")

    def get_state(self) -> str:
        """Get current circuit breaker state."""
        return self.state

    def get_stats(self) -> dict:
        """Get circuit breaker statistics."""
        return {
            "name": self.name,
            "state": self.state,
            "failure_count": self.failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "last_failure_time": self.last_failure_time,
        }

    def _log(self, message: str) -> None:
        """Log circuit breaker events."""
        print(f"[CircuitBreaker:{self.name}] {message}")

    async def is_healthy(self) -> bool:
        """Check if circuit breaker is in healthy state (CLOSED or HALF_OPEN)."""
        return self.state in ["CLOSED", "HALF_OPEN"]

    async def wait_for_recovery(self, timeout: Optional[int] = None) -> bool:
        """
        Wait for circuit breaker to recover.

        Args:
            timeout: Maximum time to wait in seconds

        Returns:
            True if recovered, False if timeout reached
        """
        start_time = time.time()

        while self.state == "OPEN":
            if timeout and (time.time() - start_time) > timeout:
                return False
            await asyncio.sleep(1)

        return True


class FallbackCircuitBreaker(CircuitBreaker):
    """
    Circuit Breaker with built-in fallback mechanism.
    """

    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: int = 60,
        expected_exception: tuple = (Exception,),
        name: str = "FallbackCircuitBreaker",
        fallback_func: Optional[Callable[..., Coroutine[Any, Any, T]]] = None,
    ):

        super().__init__(failure_threshold, recovery_timeout, expected_exception, name)
        self.fallback_func = fallback_func

    async def call_with_fallback(
        self, func: Callable[..., Coroutine[Any, Any, T]], *args, **kwargs
    ) -> Tuple[T, bool]:
        """
        Execute function with circuit breaker protection and fallback.

        Args:
            func: Async function to execute
            *args: Function arguments
            **kwargs: Function keyword arguments

        Returns:
            Tuple of (result, is_fallback_used)
        """
        try:
            result = await self.call(func, *args, **kwargs)
            return result, False
        except Exception as e:
            if self.fallback_func:
                self._log(f"Using fallback due to: {e}")
                fallback_result = await self.fallback_func(*args, **kwargs)
                return fallback_result, True
            else:
                raise e


def create_openai_circuit_breaker(name: str = "OpenAI") -> CircuitBreaker:
    return CircuitBreaker(
        failure_threshold=100,
        recovery_timeout=10,
        expected_exception=(Exception,),
        name=name,
    )


def create_http_circuit_breaker(name: str = "HTTP") -> CircuitBreaker:
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=30,
        expected_exception=(Exception,),
        name=name,
    )


def create_telegram_circuit_breaker(name: str = "Telegram") -> CircuitBreaker:
    return CircuitBreaker(
        failure_threshold=3,
        recovery_timeout=60,
        expected_exception=(Exception,),
        name=name,
    )
