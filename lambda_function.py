import json
from base64 import b64decode
from typing import Dict
from urllib.parse import parse_qs

import boto3
from aws_lambda_powertools import Logger
from aws_lambda_powertools.utilities.typing import LambdaContext

sqs = boto3.client("sqs")
sns = boto3.client("sns")
# queue_url = 'https://sqs.eu-west-1.amazonaws.com/712531873081/CoffeeOrderQueue.fifo'
queue_url = "https://sqs.eu-west-1.amazonaws.com/712531873081/CoffeeOrderQueueStandart"
sns_topic_arn_base = "arn:aws:sns:eu-west-1:712531873081:drink-order-topic-for-"

logger = Logger()


@logger.inject_lambda_context(log_event=True)
def lambda_handler(event: Dict, context: LambdaContext):

    body = (
        b64decode(event["body"]).decode("utf-8")
        if event["isBase64Encoded"]
        else event["body"]
    )
    logger.info(body)

    data = parse_qs(body)
    name = data["name"][0]
    email = data["email"][0]
    drink = data["drink"][0]

    topic_arn = sns_topic_arn_base + email

    try:
        topic = sns.get_topic_attributes(TopicArn=topic_arn)
        subscribers_no = topic["SubscriptionsConfirmed"]
        if subscribers_no == 0:
            return {
                "statusCode": 200,
                "body": json.dumps(
                    "Please confirm your email and then resubmit your drink"
                ),
            }
    except boto3.exceptions.ClientError:
        # You need to create the topic and subsribe the email here
        return {
            "statusCode": 200,
            "body": json.dumps(
                "Please confirm your email and then resubmit your drink"
            ),
        }

    messageToSQS = {"name": name, "email": email, "drink": drink}

    sqsresponce = sqs.send_message(
        QueueUrl=queue_url, MessageBody=json.dumps(messageToSQS)
    )

    return {
        "statusCode": 200,
        "body": f"""
            Thanks for the order! You will receive a message on email "{email}" when
            your drink is ready. Your order: "{drink}" for "{name}"
        """,
    }
