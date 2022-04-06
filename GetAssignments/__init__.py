import logging
import mechanicalsoup
import azure.functions as func
from main import getRealTimeCurrentRefAssignments

import os

def main(req: func.HttpRequest) -> func.HttpResponse:
    logging.info('Python HTTP trigger function processed a request.')
    x = os.environ.get("mslUsername", "fuck")
    name = req.params.get('name')
    if not name:
        try:
            req_body = req.get_json()
        except ValueError:
            pass
        else:
            name = req_body.get('name')

    br = mechanicalsoup.StatefulBrowser(soup_config={ 'features': 'lxml'})
    br.addheaders = [('User-agent', 'Chrome')]
    current = getRealTimeCurrentRefAssignments(br)

    return func.HttpResponse(
            str(current),
            status_code=200
        )
