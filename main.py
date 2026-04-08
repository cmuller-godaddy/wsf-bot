from time import sleep
import traceback
import datetime
import logging

from client.client import fetch_ferry_schedule
from client.types import VehicleSize, VehicleHeight, FerryRequest
from config.config import read_config
from config.types import Config, ConfigParser
from notifications.discord import send_notification
from notifications.types import FoundAvailableNotification

logging.basicConfig(
    format='%(asctime)s %(levelname)s %(message)s',
    level=logging.INFO,
)
logger = logging.getLogger(__name__)


def run(config: Config):
    requests = config['requests']

    logger.info(f'Checking {len(requests)} ferry requests...')

    for request in requests:
        logger.info(
            f'Checking for a ferry from ' +
            f'{request["terminal_from"]} to {request["terminal_to"]} on {request["sailing_date"]} ' +
            f'with vehicle size {request["vehicle_size"]} / {request["vehicle_height"]}.'
        )

        ferry_request = FerryRequest(
            terminal_from=request['terminal_from'].lower(),
            terminal_to=request['terminal_to'].lower(),
            sailing_date=request['sailing_date'].lower(),
            sailing_time_from=request['sailing_time_from'] if 'sailing_time_from' in request else None,
            sailing_time_to=request['sailing_time_to'] if 'sailing_time_to' in request else None,
            vehicle_size=VehicleSize.from_string(request['vehicle_size'].lower()),
            vehicle_height=VehicleHeight.from_string(request['vehicle_height'].lower()),
        )

        try:
            schedule = fetch_ferry_schedule(request=ferry_request)
        except Exception as error:
            logger.error('Failed to fetch ferry schedule due to: %s', error)
            continue

        has_available = any(entry.available for entry in schedule.entries)

        available = list(filter(lambda x: x.available, schedule.entries))

        if has_available:
            logger.info(f'Found {len(available)} ferries available!')
            send_notification(
                notification=FoundAvailableNotification(schedule=schedule),
                webhook=config['discord']['webhook']
            )
        else:
            logger.info('Found no ferries available.')


if __name__ == '__main__':

    logger.info('Starting wsf-bot script...')

    run_config = read_config()

    while True:
        run(run_config)
        logger.info(f'Sleeping for {run_config["interval"]} seconds...')
        sleep(run_config['interval'])
