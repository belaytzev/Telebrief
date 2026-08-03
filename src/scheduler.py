"""
Scheduler for automated daily digest generation.
"""

import asyncio
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from src.config_loader import Config
from src.core import generate_and_send_digest


class DigestScheduler:
    """Schedules daily digest generation."""

    def __init__(self, config: Config, logger: logging.Logger):
        """
        Initialize scheduler.

        Args:
            config: Application configuration
            logger: Logger instance
        """
        self.config = config
        self.logger = logger
        self.scheduler = AsyncIOScheduler()
        self.is_running = False

    def start(self):
        """Start the scheduler."""
        if self.is_running:
            self.logger.warning("Scheduler already running")
            return

        # Parse schedule time
        hour, minute = self._parse_schedule_time()

        # Create cron trigger for daily execution
        trigger = CronTrigger(hour=hour, minute=minute, timezone=self.config.settings.timezone)

        # Add job
        self.scheduler.add_job(
            func=self._scheduled_digest_job,
            trigger=trigger,
            id="daily_digest",
            name="Daily Digest Generation",
            replace_existing=True,
        )

        # Start scheduler
        self.scheduler.start()
        self.is_running = True

        next_run = self.scheduler.get_job("daily_digest").next_run_time
        self.logger.info("✅ Scheduler started")
        self.logger.info(
            f"⏰ Next digest scheduled for: {next_run} {self.config.settings.timezone}"
        )

    def stop(self):
        """Stop the scheduler."""
        if self.scheduler.running:
            self.scheduler.shutdown()
            self.is_running = False
            self.logger.info("Scheduler stopped")

    async def _scheduled_digest_job(self):
        """Scheduled job that runs daily."""
        self.logger.info("=" * 60)
        self.logger.info("📅 SCHEDULED DIGEST JOB STARTED")
        self.logger.info("=" * 60)

        try:
            success = await generate_and_send_digest(
                config=self.config, logger=self.logger, hours=self.config.settings.lookback_hours
            )

            if success:
                self.logger.info("✅ Scheduled digest completed successfully")
            else:
                self.logger.error("❌ Scheduled digest failed to send")

        except Exception as e:
            self.logger.error(f"❌ Scheduled digest job failed: {e}", exc_info=True)

    def _parse_schedule_time(self) -> tuple[int, int]:
        """
        Parse schedule time from config.

        Returns:
            Tuple of (hour, minute)
        """
        time_str = self.config.settings.schedule_time
        try:
            hour, minute = map(int, time_str.split(":"))
            return hour, minute
        except Exception:
            self.logger.warning(f"Invalid schedule time '{time_str}', using default 08:00")
            return 8, 0

    def get_next_run_time(self) -> str:
        """
        Get next scheduled run time.

        Returns:
            Formatted time string
        """
        if not self.is_running:
            return "Scheduler not running"

        job = self.scheduler.get_job("daily_digest")
        if job and job.next_run_time:
            return str(job.next_run_time.strftime("%Y-%m-%d %H:%M:%S %Z"))
        return "No job scheduled"


async def main():
    """Test scheduler."""
    from src.config_loader import load_config
    from src.utils import setup_logging

    config = load_config()
    logger = setup_logging(config.log_level)

    scheduler = DigestScheduler(config, logger)
    scheduler.start()

    logger.info("Scheduler running. Press Ctrl+C to stop.")
    logger.info(f"Next run: {scheduler.get_next_run_time()}")

    try:
        # Keep running
        while True:
            await asyncio.sleep(60)
    except KeyboardInterrupt:
        logger.info("Stopping scheduler...")
        scheduler.stop()


if __name__ == "__main__":
    asyncio.run(main())
