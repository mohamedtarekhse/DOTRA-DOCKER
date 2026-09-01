import logging

from .zone_monitor import monitor_loop

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("stream-processor")


def main():
    logger.info("Starting Stream Processor...")
    monitor_loop()


if __name__ == "__main__":
    main()
