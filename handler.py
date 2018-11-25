import json
import time
import boto3
from boto3.dynamodb.conditions import Key
from botocore.vendored import requests
import config


MY_DYNAMODB = boto3.resource('dynamodb', region_name='us-west-2')
INBOUND_TBL = MY_DYNAMODB.Table('forward-sms')


def make_response(code, message, detail=None):
    """Response Generator for Logging."""
    return {
        "statusCode": code,
        "message": message,
        "details": detail
        }


def receive_inbound_sms(event, context):
    """Handle incoming events."""
    print('INFO: Inbound SMS Call Received')
    is_duplicate = False

    try:
        event_body = json.loads(event['body'])
    except TypeError:  # lambda test event
        event_body = event['body']

    called_mdr = event_body['data']['id']
    called_mdr_count = INBOUND_TBL.query(KeyConditionExpression=Key('inbound_mdr')
                                         .eq(called_mdr))['Count']

    if called_mdr_count > 0:
        is_duplicate = True

    if is_duplicate:
        print("ERROR: Duplicated call", called_mdr)
    else:
        log_inbound_sms(event_body, forward=True)


def log_inbound_sms(event, forward=True):
    """Log inbound Information."""
    mdr = event['data']['id']
    from_number = event['data']['attributes']['from']
    to_number = event['data']['attributes']['to']
    message_body = event['data']['attributes']['body']
    timestamp = event['data']['attributes']['timestamp']
    forward_mdr = "Not Sent"

    print("INFO: Inbound Log", mdr)

    # update inbound item to dynamo
    log_item = {
        'inbound_mdr': mdr,
        'from': from_number,
        'to': to_number,
        'body': message_body,
        'time': timestamp,
        'forward_mdr': forward_mdr
        }
    try:
        INBOUND_TBL.put_item(Item=log_item)
        inbound_log_result = make_response(200,
                                           "Inbound SMS saved to Dynamo",
                                           detail=log_item)
        print("INFO:", inbound_log_result)
        if forward:
            forward_sms(from_number, to_number, message_body, mdr)
    except Exception as e:
        inbound_log_result = make_response(500,
                                           'Dynamo Error during Inbound: {}'
                                           .format(e), detail=log_item)
        print("ERROR:", inbound_log_result)


def forward_sms(from_number, to_number, message_body, mdr):
    """Forward SMS to FORWARD_NUMBER in config."""
    print("INFO: Forward SMS")
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


def log_outbound_sms(forward_response, mdr):
    """Log Forward Information."""
    forward_mdr = forward_response['data']['id']

    print("INFO: Forward Log", forward_mdr)

    try:
        INBOUND_TBL.update_item(
            Key={'inbound_mdr': mdr},
            UpdateExpression="SET forward_mdr = :f",
            ExpressionAttributeValues={':f': forward_mdr},
            ReturnValues="UPDATED_NEW"
        )
        forward_log_result = make_response(200, "Forward SMS saved to Dynamo")
        print("INFO:", forward_log_result)
    except Exception as e:
        forward_log_result = make_response(500,
                                           'Dynamo Error during Forward: {}'
                                           .format(e))
        print("ERROR:", forward_log_result)
