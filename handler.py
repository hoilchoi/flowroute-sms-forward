import json
import boto3
from botocore.vendored import requests
import config


MY_DYNAMODB = boto3.resource('dynamodb', region_name='us-west-2')
INBOUND_TBL = MY_DYNAMODB.Table('inbound-sms')
OUTBOUND_TBL = MY_DYNAMODB.Table('outbound-sms')


def make_response(code, message, detail=None):
    """Response generator."""
    return {
        "statusCode": code,
        "message": message,
        "details": detail
        }


def log_inbound_sms(event, forward=True):
    """Log inbound SMS."""
    mdr = event['data']['id']
    from_number = event['data']['attributes']['from']
    to_number = event['data']['attributes']['to']
    message_body = event['data']['attributes']['body']
    timestamp = event['data']['attributes']['timestamp']
    direction = event['data']['attributes']['direction']

    # update inbound item to dynamo
    log_item = {
        'id': mdr,
        'from': from_number,
        'to': to_number,
        'body': message_body,
        'time': timestamp,
        'direction': direction,
        }
    try:
        INBOUND_TBL.put_item(Item=log_item)
    except Exception as e:
        return make_response(500, 'Dynamo Error: {}'
                             .format(e), detail=log_item)

    # forward message
    if forward:
        # print("forwarding")
        send_url = config.sms_url
        headers = {'content-type': 'application/json'}
        auth = (config.api_key, config.api_secret)
        message_body = ("""FORWARDED MESSAGE\n
                        Original Sender: {}\n
                        Original Receiver: {}\n
                        {}"""
                        .format(from_number, to_number, message_body))
        to_number = "12532735442"
        body = {"to": to_number,
                "from": config.from_number,
                "body": message_body,
                }

        # sent outbound sms
        requests.post(url=send_url, auth=auth, json=body,
                      headers=headers)

    return make_response(200, "SMS saved to Dynamo", detail=log_item)


def log_outbound_dlr(event):
    """Log outbound sms dlr."""
    mdr = event['data']['id']
    from_number = event['data']['attributes']['from']
    to_number = event['data']['attributes']['to']
    message_body = event['data']['attributes']['body']
    timestamp = event['data']['attributes']['timestamp']
    direction = event['data']['attributes']['direction']

    log_item = {
        'id': mdr,
        'from': from_number,
        'to': to_number,
        'body': message_body,
        'time': timestamp,
        'direction': direction,
        }
    try:
        OUTBOUND_TBL.put_item(Item=log_item)
    except Exception as e:
        return make_response(500, 'Dynamo Error: {}'
                             .format(e), detail=log_item)
    return make_response(200, "SMS saved to Dynamo", detail=log_item)


def log_outbound_sms(event):
    """Log outbound sms result."""
    mdr = event['data']['id']

    # update outbound to dynamo
    log_item = {
        'id': mdr,
        'from': config.from_number,
        'direction': "forward",
        # make it so that orig sender, orig to becomes column in db
        # then rename outbound-sms to forward-sms
        }
    try:
        OUTBOUND_TBL.put_item(Item=log_item)
    except Exception as e:
        return make_response(500, 'Dynamo Error: {}'
                             .format(e), detail=log_item)

    return make_response(200, "SMS saved to Dynamo", detail=log_item)


def receive_inbound_sms(event):
    """Handle incoming events."""
    print("called")
    print(event)
    event_body = json.loads(event['body'])
    # sms = event

    if event_body['data']['attributes']['delivery_receipts']:
        response = log_outbound_dlr(event_body)
    elif event_body['data']['attributes']['direction'] == "inbound":
        response = log_inbound_sms(event_body, forward=True)
    else:
        response = log_outbound_sms(event_body)
    return response
