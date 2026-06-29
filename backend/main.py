from eod_data.Ticker_EOD_Manager import Tickers_EOD_Manager
from storage.TickersDBManager import TickersDBManager
from sync.SyncManager import SyncManager

from utils.ConsoleLogger import ConsoleLogger
from utils.Banner import print_banner, print_backend_banner

import pandas as pd
import json
from pathlib import Path

CONFIG_PATH = Path(__file__).parent / "config.json"

def load_config():
    with open(CONFIG_PATH, "r", encoding="utf-8") as file:
        config = json.load(file)
        return config["tickers"], config["periods"], config["db_name"]

def main():
    logger = ConsoleLogger()

    print_banner()

    logger.section("Loading Configuration")
    tickers, periods, db_name = load_config()

    logger.info(f"Database name: {db_name}")
    logger.info(f"Tickers: {', '.join(tickers)}")
    logger.info(f"Periods: {', '.join(map(str, periods))}")

    logger.section("Initializing Managers")

    db_manager = TickersDBManager(db_name, tickers)
    sync_manager = SyncManager(tickers, db_manager)

    logger.success("Database manager initialized")
    logger.success("Sync manager initialized")

    logger.section("Checking Sync Status")

    sync_status = sync_manager.get_sync_status()

    synced_tickers = [
        ticker for ticker, status in sync_status.items()
        if status["is_synced"]
    ]

    unsynced_tickers = [
        ticker for ticker, status in sync_status.items()
        if not status["is_synced"]
    ]

    logger.info(f"Synced tickers: {len(synced_tickers)}")
    logger.info(f"Unsynced tickers: {len(unsynced_tickers)}")

    if synced_tickers:
        logger.success(f"Already synced: {', '.join(synced_tickers)}")

    if unsynced_tickers:
        logger.warning(f"Need syncing: {', '.join(unsynced_tickers)}")

        logger.section("Fetching EOD Data")

        eod_manager = Tickers_EOD_Manager(unsynced_tickers, periods=periods)
        all_data = eod_manager.extract_all_tickers_data(sync_status)

        logger.success("Finished fetching data")

        logger.section("Saving Data to Database")

        for ticker in unsynced_tickers:
            logger.subsection(f"Syncing {ticker}")

            daily_df, weekly_df, monthly_df = all_data[ticker]
            full_df = pd.concat([daily_df, weekly_df, monthly_df], axis=1)

            logger.info(f"Daily rows:   {len(daily_df)}")
            logger.info(f"Weekly rows:  {len(weekly_df)}")
            logger.info(f"Monthly rows: {len(monthly_df)}")
            logger.info(f"Combined rows saved: {len(full_df)}")

            db_manager.get_ticker(ticker).add_dataframe(full_df)

            logger.success(f"{ticker} synced successfully")

    else:
        logger.success("All tickers are already synced. No update needed.")


    logger.section("Closing Database Connection")

    db_manager.close()

    logger.success("Database connection closed successfully")

    print()

if __name__ == "__main__":
    main()