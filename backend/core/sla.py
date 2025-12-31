"""
SLA Business Hours Calculator.
Provides accurate SLA calculations that respect business hours configuration.
"""
from datetime import datetime, timedelta, timezone, time as dt_time
from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class BusinessHoursCalculator:
    """
    Calculator for SLA times that respects business hours.

    Business hours are defined by:
    - Start time (e.g., 09:00)
    - End time (e.g., 18:00)
    - Business days (e.g., [1, 2, 3, 4, 5] for Monday to Friday)
    """

    def __init__(
        self,
        start_hour: int = 9,
        start_minute: int = 0,
        end_hour: int = 18,
        end_minute: int = 0,
        business_days: list = None
    ):
        """
        Initialize the calculator with business hours configuration.

        Args:
            start_hour: Business day start hour (0-23)
            start_minute: Business day start minute (0-59)
            end_hour: Business day end hour (0-23)
            end_minute: Business day end minute (0-59)
            business_days: List of ISO weekdays (1=Monday, 7=Sunday)
        """
        self.start_time = dt_time(start_hour, start_minute)
        self.end_time = dt_time(end_hour, end_minute)
        self.business_days = business_days or [1, 2, 3, 4, 5]  # Mon-Fri

        # Calculate business hours per day in minutes
        self.business_minutes_per_day = (
            (end_hour * 60 + end_minute) - (start_hour * 60 + start_minute)
        )

    @classmethod
    def from_policy(cls, policy) -> 'BusinessHoursCalculator':
        """
        Create a calculator from an SLAPolicy model.

        Args:
            policy: SLAPolicy model instance

        Returns:
            BusinessHoursCalculator instance
        """
        # Parse time strings (HH:MM format)
        start_parts = policy.business_start.split(':')
        end_parts = policy.business_end.split(':')

        return cls(
            start_hour=int(start_parts[0]),
            start_minute=int(start_parts[1]) if len(start_parts) > 1 else 0,
            end_hour=int(end_parts[0]),
            end_minute=int(end_parts[1]) if len(end_parts) > 1 else 0,
            business_days=policy.business_days or [1, 2, 3, 4, 5]
        )

    def is_business_day(self, dt: datetime) -> bool:
        """Check if the given datetime falls on a business day."""
        # isoweekday(): Monday=1, Sunday=7
        return dt.isoweekday() in self.business_days

    def is_business_hours(self, dt: datetime) -> bool:
        """Check if the given datetime falls within business hours."""
        if not self.is_business_day(dt):
            return False
        current_time = dt.time()
        return self.start_time <= current_time < self.end_time

    def get_next_business_start(self, dt: datetime) -> datetime:
        """
        Get the start of the next business period from the given datetime.

        If currently in business hours, returns the current datetime.
        Otherwise, returns the start of the next business day.
        """
        # If currently in business hours, return as-is
        if self.is_business_hours(dt):
            return dt

        # If it's a business day but before business hours, return today's start
        if self.is_business_day(dt) and dt.time() < self.start_time:
            return dt.replace(
                hour=self.start_time.hour,
                minute=self.start_time.minute,
                second=0,
                microsecond=0
            )

        # Move to the next day
        next_day = dt + timedelta(days=1)
        next_day = next_day.replace(
            hour=self.start_time.hour,
            minute=self.start_time.minute,
            second=0,
            microsecond=0
        )

        # Find next business day
        while not self.is_business_day(next_day):
            next_day += timedelta(days=1)

        return next_day

    def get_business_end_today(self, dt: datetime) -> datetime:
        """Get the end of business hours for the given day."""
        return dt.replace(
            hour=self.end_time.hour,
            minute=self.end_time.minute,
            second=0,
            microsecond=0
        )

    def add_business_minutes(self, start: datetime, minutes: int) -> datetime:
        """
        Add a number of business minutes to a start datetime.

        This correctly handles weekends and outside-of-hours calculations.

        Args:
            start: Starting datetime
            minutes: Number of business minutes to add

        Returns:
            The resulting datetime after adding business minutes
        """
        if minutes <= 0:
            return start

        remaining_minutes = minutes
        current = self.get_next_business_start(start)

        while remaining_minutes > 0:
            # Get end of current business day
            day_end = self.get_business_end_today(current)

            # Calculate minutes remaining in current day
            if current.date() == day_end.date():
                current_time_minutes = current.hour * 60 + current.minute
                end_time_minutes = self.end_time.hour * 60 + self.end_time.minute
                minutes_left_today = end_time_minutes - current_time_minutes
            else:
                minutes_left_today = 0

            if remaining_minutes <= minutes_left_today:
                # Can complete within today
                return current + timedelta(minutes=remaining_minutes)
            else:
                # Use up today's remaining time and move to next business day
                remaining_minutes -= minutes_left_today
                current = self.get_next_business_start(day_end + timedelta(seconds=1))

        return current

    def calculate_business_minutes_between(
        self,
        start: datetime,
        end: datetime
    ) -> int:
        """
        Calculate the number of business minutes between two datetimes.

        Args:
            start: Start datetime
            end: End datetime

        Returns:
            Number of business minutes elapsed
        """
        if end <= start:
            return 0

        total_minutes = 0
        current = self.get_next_business_start(start)

        while current < end:
            day_end = self.get_business_end_today(current)

            if day_end >= end:
                # End is today
                current_time_minutes = current.hour * 60 + current.minute
                end_time_minutes = end.hour * 60 + end.minute
                total_minutes += max(0, end_time_minutes - current_time_minutes)
                break
            else:
                # Count remaining minutes today
                current_time_minutes = current.hour * 60 + current.minute
                end_time_minutes = self.end_time.hour * 60 + self.end_time.minute
                total_minutes += max(0, end_time_minutes - current_time_minutes)

                # Move to next business day
                current = self.get_next_business_start(day_end + timedelta(seconds=1))

        return total_minutes


def calculate_sla_due_date(
    created_at: datetime,
    sla_minutes: int,
    policy = None,
    use_business_hours: bool = True
) -> datetime:
    """
    Calculate SLA due date based on policy configuration.

    Args:
        created_at: When the ticket was created
        sla_minutes: Number of minutes for the SLA target
        policy: Optional SLAPolicy model with business hours config
        use_business_hours: Whether to use business hours (default True)

    Returns:
        The datetime when the SLA will be due
    """
    if not use_business_hours or policy is None or not policy.business_hours_only:
        # Simple calculation - just add minutes
        return created_at + timedelta(minutes=sla_minutes)

    # Use business hours calculator
    calculator = BusinessHoursCalculator.from_policy(policy)
    return calculator.add_business_minutes(created_at, sla_minutes)


def calculate_elapsed_business_time(
    start: datetime,
    end: datetime,
    policy = None,
    use_business_hours: bool = True
) -> int:
    """
    Calculate elapsed business time between two datetimes.

    Args:
        start: Start datetime
        end: End datetime
        policy: Optional SLAPolicy model with business hours config
        use_business_hours: Whether to use business hours (default True)

    Returns:
        Number of minutes elapsed (business or total)
    """
    if not use_business_hours or policy is None or not policy.business_hours_only:
        # Simple calculation
        delta = end - start
        return int(delta.total_seconds() / 60)

    # Use business hours calculator
    calculator = BusinessHoursCalculator.from_policy(policy)
    return calculator.calculate_business_minutes_between(start, end)


def check_sla_status(
    ticket,
    policy = None
) -> Tuple[bool, Optional[int]]:
    """
    Check the SLA status of a ticket.

    Args:
        ticket: Ticket model instance
        policy: Optional SLAPolicy model

    Returns:
        Tuple of (is_breached, minutes_remaining)
        minutes_remaining is None if ticket is closed/resolved
    """
    now = datetime.now(timezone.utc)

    # Closed or resolved tickets don't have active SLA
    if ticket.status in ("closed", "resolved"):
        return (ticket.sla_breached, None)

    # Check if SLA is already breached
    if ticket.sla_due_date and now > ticket.sla_due_date:
        return (True, 0)

    # Calculate remaining time
    if ticket.sla_due_date:
        if policy and policy.business_hours_only:
            calculator = BusinessHoursCalculator.from_policy(policy)
            remaining = calculator.calculate_business_minutes_between(now, ticket.sla_due_date)
        else:
            remaining = int((ticket.sla_due_date - now).total_seconds() / 60)

        return (False, remaining)

    return (False, None)
