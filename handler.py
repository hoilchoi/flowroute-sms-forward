import json
import time
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
    print("INFO: log inbound sms start")
    mdr = event['data']['id']
    from_number = event['data']['attributes']['from']
    to_number = event['data']['attributes']['to']
    message_body = event['data']['attributes']['body']
    timestamp = event['data']['attributes']['timestamp']
    direction = event['data']['attributes']['direction']
    forward_mdr = "Not Sent"

    # update inbound item to dynamo
    log_item = {
        'id': mdr,
        'from': from_number,
        'to': to_number,
        'body': message_body,
        'time': timestamp,
        'direction': direction,
        'forward_mdr': forward_mdr
        }
    try:
        INBOUND_TBL.put_item(Item=log_item)
    except Exception as e:
        return make_response(500, 'Dynamo Error: {}'
                             .format(e), detail=log_item)

    # forward message
    if forward:
        print("INFO: forwarding sms start")
        send_url = config.SMS_URL
        headers = {'content-type': 'application/json'}
        auth = (config.API_KEY, config.API_SECRET)
        message_body = ("FORWARDED MESSAGE\n"
                        "Original From: {}\n"
                        "Original To: {}\n"
                        "Body: {}").format(from_number, to_number, message_body)
        to_number = config.FORWARD_NUMBER
        body = {"to": to_number,
                "from": config.FROM_NUMBER,
                "body": message_body,
                }

        # sent outbound sms
        forward_message = requests.post(url=send_url, auth=auth, json=body,
                                        headers=headers)
        time.sleep(3)
        forward_response = forward_message.json()
        log_outbound_sms(forward_response, mdr)

    return make_response(200, "SMS saved to Dynamo", detail=log_item)


def log_outbound_sms(event, mdr):
    """Log outbound sms result."""
    print("INFO: log outbound sms start")
    forward_mdr = event['data']['id']

    try:
        INBOUND_TBL.update_item(
            Key={'id': mdr},
            UpdateExpression="SET forward_mdr = :f",
            ExpressionAttributeValues={':f': forward_mdr},
            ReturnValues="UPDATED_NEW"
        )

    except Exception as e:
        return make_response(500, 'Dynamo Error: {}'
                             .format(e))

    return make_response(200, "SMS saved to Dynamo")


def receive_inbound_sms(event, context):
    """Handle incoming events."""
    print('INFO: Inbound SMS Call Received')
    event_body = json.loads(event['body'])
    mdr = event_body['data']['id']

    try:
        INBOUND_TBL.get_item(Key={'id': mdr})['Item']['id']
        print("ERROR: Duplicated call")
    except KeyError:
        response = log_inbound_sms(event_body, forward=True)
        return response
