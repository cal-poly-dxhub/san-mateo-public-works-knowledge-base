import json
from urllib.request import Request, urlopen

SUCCESS = "SUCCESS"
FAILED = "FAILED"


def send(
    event,
    context,
    responseStatus,
    responseData,
    physicalResourceId=None,
    noEcho=False,
    reason=None,
):
    responseUrl = event["ResponseURL"]

    responseBody = {
        "Status": responseStatus,
        "Reason": reason or f"See CloudWatch Log Stream: {context.log_stream_name}",
        "PhysicalResourceId": physicalResourceId or context.log_stream_name,
        "StackId": event["StackId"],
        "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"],
        "NoEcho": noEcho,
        "Data": responseData,
    }

    json_responseBody = json.dumps(responseBody).encode("utf-8")

    try:
        request = Request(responseUrl, data=json_responseBody, method="PUT")
        request.add_header("Content-Type", "")
        request.add_header("Content-Length", str(len(json_responseBody)))
        response = urlopen(request)
        print(f"Status code: {response.status}")
    except Exception as e:
        print(f"send(..) failed: {e}")
