from playwright.sync_api import sync_playwright
import datetime
import logging

from client.types import VehicleSize, VehicleHeight, FerryScheduleEntry, FerrySchedule, FerryRequest

WSF_ENDPOINT = 'https://secureapps.wsdot.wa.gov/ferries/reservations/vehicle/SailingSchedule.aspx'

TERMINAL_MAP = {
    'anacortes': '1',
    'friday harbor': '10',
    'coupeville': '11',
    'lopez island': '13',
    'orcas island': '15',
    'port townsend': '17',
    'shaw island': '18'
}

VEHICLE_MAP = {
    VehicleSize.VEHICLE_UNDER_22: '3'
}

VEHICLE_HEIGHT_MAP = {
    VehicleHeight.UP_TO_7_2_TALL: '1000',
    VehicleHeight.FROM_7_2_TO_7_6_TALL: '1001',
    VehicleHeight.FROM_7_6_TO_13_TALL: '6'
}

TIME_FORMAT = '%I:%M %p'

MAX_RETRIES = 3

logger = logging.getLogger(__name__)

def _fill_and_submit(page, request: FerryRequest):
    page.goto(WSF_ENDPOINT, wait_until='domcontentloaded', timeout=15000)

    page.locator('#MainContent_dlFromTermList').select_option(value=TERMINAL_MAP[request.terminal_from])
    page.locator('#MainContent_dlToTermList').wait_for(state='attached')
    page.locator('#MainContent_dlToTermList').select_option(value=TERMINAL_MAP[request.terminal_to])

    page.evaluate(f"""
        const dp = $('#MainContent_txtDatePicker');
        dp.datepicker('setDate', '{request.sailing_date}');
        dp.trigger('change');
    """)

    page.locator('#MainContent_dlVehicle').select_option(value=VEHICLE_MAP[request.vehicle_size])
    page.locator('#MainContent_ddlCarTruck14To22').wait_for(state='attached')
    page.locator('#MainContent_ddlCarTruck14To22').select_option(value=VEHICLE_HEIGHT_MAP[request.vehicle_height])

    page.locator('#MainContent_linkBtnContinue').click()
    try:
        page.locator('#MainContent_gvschedule').wait_for(state='visible', timeout=30000)
    except Exception:
        logger.debug(f'Page URL: {page.url}')
        logger.debug(f'Page title: {page.title()}')
        logger.debug(f'Page text: {page.inner_text("body")[:3000]}')
        raise

    return page.locator('#MainContent_gvschedule tr')

def fetch_ferry_schedule(request: FerryRequest):
    if request.terminal_from not in TERMINAL_MAP:
        raise TypeError(f'Unknown terminal name provided: {request.terminal_from}')

    if request.terminal_to not in TERMINAL_MAP:
        raise TypeError(f'Unknown terminal name provided: {request.terminal_to}')

    with sync_playwright() as playwright:
        chrome = playwright.chromium
        logger.info('Launching browser...')
        browser = chrome.launch()
        try:
            page = browser.new_page()
            page.set_default_timeout(15000)

            logger.info('Navigating to WSF schedule page...')
            rows = None
            for attempt in range(MAX_RETRIES):
                try:
                    rows = _fill_and_submit(page, request)
                    if rows.count() > 0:
                        break
                    logger.warning(f'No schedule table found, retrying ({attempt + 1}/{MAX_RETRIES})...')
                except Exception as e:
                    logger.warning(f'Attempt {attempt + 1}/{MAX_RETRIES} failed: {e}')
                    if attempt == MAX_RETRIES - 1:
                        raise

            content = rows.all_inner_texts()
            logger.debug(f'Page title: {page.title()}')
            logger.debug(f'Page URL: {page.url}')
            logger.debug(f'Found {len(content)} rows, first row: {content[0] if content else "none"}')
        finally:
            logger.info('Closing browser...')
            browser.close()

    sailing_time_from = \
        datetime.datetime.strptime(request.sailing_time_from, TIME_FORMAT).time() if request.sailing_time_from else None

    sailing_time_to = \
        datetime.datetime.strptime(request.sailing_time_to, TIME_FORMAT).time() if request.sailing_time_to else None

    entries = []
    for entry in content[1:]:
        split = list(
            map(str.strip, filter(None, entry.split(sep='\t')))
        )

        sailing_time = datetime.datetime.strptime(split[0], TIME_FORMAT).time()

        if sailing_time_from and sailing_time < sailing_time_from:
            continue

        if sailing_time_to and sailing_time > sailing_time_to:
            continue

        entries.append(
            FerryScheduleEntry(
                sailing_time=sailing_time,
                available=any("Space Available" in s for s in split),
                vessel=split[-1]
            )
        )

    return FerrySchedule(
        sailing_date=request.sailing_date,
        terminal_from=request.terminal_from,
        terminal_to=request.terminal_to,
        entries=entries
    )
