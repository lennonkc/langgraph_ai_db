# 重试系统和熔断器实现
import time
import random
from functools import wraps
from typing import Callable, List, Type, Dict, Any
from .error_types import (
    ErrorCategory, ErrorContext, ErrorSeverity,
    BigQueryError, LLMError, DatabaseAnalystError
)

class RetryStrategy:
    """重试策略基类"""

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        raise NotImplementedError

    def get_delay(self, attempt: int) -> float:
        """获取重试延迟时间"""
        raise NotImplementedError

class ExponentialBackoffStrategy(RetryStrategy):
    """指数退避重试策略"""

    def __init__(self,
                 max_attempts: int = 3,
                 base_delay: float = 1.0,
                 max_delay: float = 60.0,
                 jitter: bool = True):
        self.max_attempts = max_attempts
        self.base_delay = base_delay
        self.max_delay = max_delay
        self.jitter = jitter

    def should_retry(self, error: Exception, attempt: int) -> bool:
        """判断是否应该重试"""
        if attempt >= self.max_attempts:
            return False

        # Define retryable error types
        retryable_errors = (
            BigQueryError,
            LLMError,
            DatabaseAnalystError,
            ConnectionError,
            TimeoutError
        )

        if not isinstance(error, retryable_errors):
            return False

        # Check error category for retry eligibility
        if hasattr(error, 'category'):
            non_retryable_categories = [
                ErrorCategory.BIGQUERY_SYNTAX,
                ErrorCategory.BIGQUERY_PERMISSION,
                ErrorCategory.INVALID_QUESTION,
                ErrorCategory.UNSUPPORTED_REQUEST
            ]

            if error.category in non_retryable_categories:
                return False

        return True

    def get_delay(self, attempt: int) -> float:
        """计算重试延迟时间"""
        delay = self.base_delay * (2 ** attempt)
        delay = min(delay, self.max_delay)

        if self.jitter:
            delay *= (0.5 + random.random() * 0.5)

        return delay

def with_retry(strategy: RetryStrategy = None):
    """重试装饰器"""

    if strategy is None:
        strategy = ExponentialBackoffStrategy()

    def decorator(func: Callable):
        @wraps(func)
        def wrapper(*args, **kwargs):
            last_exception = None
            attempt = 0

            while True:
                try:
                    return func(*args, **kwargs)

                except Exception as e:
                    last_exception = e
                    attempt += 1

                    if not strategy.should_retry(e, attempt):
                        # Import here to avoid circular imports
                        try:
                            from .error_logging import log_error_with_context
                            # Log retry exhaustion
                            error_context = ErrorContext(
                                session_id=kwargs.get('session_id', 'unknown'),
                                step_name=func.__name__,
                                user_question=kwargs.get('user_question', ''),
                                error_category=getattr(e, 'category', ErrorCategory.VALIDATION_FAILED),
                                severity=getattr(e, 'severity', ErrorSeverity.HIGH),
                                error_message=str(e),
                                retry_count=attempt - 1
                            )
                            log_error_with_context(error_context)
                        except ImportError:
                            print(f"Error logging failed for {func.__name__}: {str(e)}")

                        raise

                    # Wait before retry
                    delay = strategy.get_delay(attempt)
                    time.sleep(delay)

                    # Log retry attempt
                    print(f"Retrying {func.__name__} (attempt {attempt}) after {delay:.2f}s delay")

        return wrapper
    return decorator

class CircuitBreaker:
    """熔断器模式实现"""

    def __init__(self,
                 failure_threshold: int = 5,
                 recovery_timeout: float = 60.0,
                 expected_exception: Type[Exception] = Exception):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.expected_exception = expected_exception
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "closed"  # closed, open, half-open

    def call(self, func: Callable, *args, **kwargs):
        """通过熔断器调用函数"""

        if self.state == "open":
            if self._should_attempt_reset():
                self.state = "half-open"
            else:
                raise CircuitBreakerOpenError("Circuit breaker is open")

        try:
            result = func(*args, **kwargs)

            # Success - reset failure count
            if self.state == "half-open":
                self.state = "closed"
            self.failure_count = 0

            return result

        except self.expected_exception as e:
            self._record_failure()
            raise

    def _record_failure(self):
        """记录失败"""
        self.failure_count += 1
        self.last_failure_time = time.time()

        if self.failure_count >= self.failure_threshold:
            self.state = "open"

    def _should_attempt_reset(self) -> bool:
        """判断是否应该尝试重置"""
        if self.last_failure_time is None:
            return False

        return time.time() - self.last_failure_time >= self.recovery_timeout

class CircuitBreakerOpenError(Exception):
    """熔断器开启错误"""
    pass