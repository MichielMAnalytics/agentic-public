import logging
import azure.functions as func
import sys
import sqlite3
import os

# Check if running in Azure production environment
if 'WEBSITE_INSTANCE_ID' in os.environ:
    # these three lines swap the stdlib sqlite3 lib with the pysqlite3 package
    __import__('pysqlite3')
    sys.modules['sqlite3'] = sys.modules.pop('pysqlite3')

app = func.FunctionApp()

@app.schedule(schedule="0 0 13 * * *", arg_name="myTimer", run_on_startup=True,
              use_monitor=False) 
def timer_trigger(myTimer: func.TimerRequest) -> None:
    if myTimer.past_due:
        logging.info('The timer is past due!')
    logging.info(sqlite3.sqlite_version)
    logging.info('Python timer trigger function executed.')
    try:
        logging.info('Calling main function...')
        from research_tweeting.main_content import main_function
        main_function()  # Attempt to run the main function
        logging.info('Main function executed successfully')
    except Exception as e:
        logging.error(f'An error occurred: {str(e)}')