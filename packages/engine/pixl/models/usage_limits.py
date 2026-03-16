"""Usage limits models for tracking provider rate limits and quotas."""

from datetime import datetime

from pydantic import BaseModel, Field


class ProviderUsageLimits(BaseModel):
    """Rate limit and quota information for an LLM provider.

    Captures both request limits and token limits from provider APIs.
    Follows the header patterns from Anthropic and OpenAI APIs.
    """

    provider: str = Field(..., description="Provider identifier (e.g., 'anthropic', 'codex')")
    model: str | None = Field(default=None, description="Model used for the request")

    # Request limits
    requests_limit: int | None = Field(default=None, description="Maximum requests per window")
    requests_remaining: int | None = Field(default=None, description="Remaining requests in window")
    requests_reset: datetime | None = Field(default=None, description="When requests reset")

    # Token limits (input)
    input_tokens_limit: int | None = Field(
        default=None, description="Maximum input tokens per window"
    )
    input_tokens_remaining: int | None = Field(default=None, description="Remaining input tokens")

    # Token limits (output)
    output_tokens_limit: int | None = Field(
        default=None, description="Maximum output tokens per window"
    )
    output_tokens_remaining: int | None = Field(default=None, description="Remaining output tokens")
    tokens_reset: datetime | None = Field(default=None, description="When token limits reset")

    # Metadata
    captured_at: datetime = Field(
        default_factory=datetime.now, description="When limits were captured"
    )
    available: bool = Field(default=True, description="False if provider doesn't expose limits")
    error: str | None = Field(
        default=None, description="Error message if limits couldn't be fetched"
    )

    def is_near_limit(self, threshold: float = 0.1) -> bool:
        """Check if any limit is below threshold percentage remaining.

        Args:
            threshold: Percentage threshold (0.1 = 10% remaining)

        Returns:
            True if any limit is below threshold
        """
        if not self.available:
            return False

        # Check request limits
        if (
            self.requests_limit
            and self.requests_remaining is not None
            and self.requests_remaining / self.requests_limit < threshold
        ):
            return True

        # Check input token limits
        if (
            self.input_tokens_limit
            and self.input_tokens_remaining is not None
            and self.input_tokens_remaining / self.input_tokens_limit < threshold
        ):
            return True

        # Check output token limits
        return bool(
            self.output_tokens_limit
            and self.output_tokens_remaining is not None
            and self.output_tokens_remaining / self.output_tokens_limit < threshold
        )

    def get_lowest_remaining_percent(self) -> float | None:
        """Get the lowest remaining percentage across all limits.

        Returns:
            Lowest percentage (0.0-1.0) or None if no limits available
        """
        percentages: list[float] = []

        if self.requests_limit and self.requests_remaining is not None:
            percentages.append(self.requests_remaining / self.requests_limit)

        if self.input_tokens_limit and self.input_tokens_remaining is not None:
            percentages.append(self.input_tokens_remaining / self.input_tokens_limit)

        if self.output_tokens_limit and self.output_tokens_remaining is not None:
            percentages.append(self.output_tokens_remaining / self.output_tokens_limit)

        return min(percentages) if percentages else None

    def format_requests(self) -> str:
        """Format request limits as a string."""
        if self.requests_limit is None or self.requests_remaining is None:
            return "n/a"
        return f"{self.requests_remaining:,}/{self.requests_limit:,}"

    def format_input_tokens(self) -> str:
        """Format input token limits as a string."""
        if self.input_tokens_limit is None or self.input_tokens_remaining is None:
            return "n/a"
        # Use k suffix for thousands
        remaining = self.input_tokens_remaining / 1000
        limit = self.input_tokens_limit / 1000
        return f"{remaining:.0f}k/{limit:.0f}k"

    def format_output_tokens(self) -> str:
        """Format output token limits as a string."""
        if self.output_tokens_limit is None or self.output_tokens_remaining is None:
            return "n/a"
        remaining = self.output_tokens_remaining / 1000
        limit = self.output_tokens_limit / 1000
        return f"{remaining:.0f}k/{limit:.0f}k"

    def format_reset(self) -> str:
        """Format reset time as relative string."""
        reset_time = self.requests_reset or self.tokens_reset
        if reset_time is None:
            return "n/a"

        now = datetime.now()
        if reset_time <= now:
            return "now"

        delta = reset_time - now
        seconds = int(delta.total_seconds())

        if seconds < 60:
            return f"{seconds}s"
        elif seconds < 3600:
            minutes = seconds // 60
            return f"{minutes} min"
        else:
            hours = seconds // 3600
            return f"{hours} hour{'s' if hours > 1 else ''}"
