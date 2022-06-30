import json
from base64 import b64decode
from urllib.parse import parse_qs

import boto3
import botocore
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.event_handler.api_gateway import APIGatewayHttpResolver
from aws_lambda_powertools.logging import correlation_paths

service = "COFFEE_APP"
logger = Logger(service=service)
tracer = Tracer(service=service)
metrics = Metrics(namespace="MyApp", service=service)
app = APIGatewayHttpResolver()


sqs = boto3.client("sqs")
sns = boto3.client("sns")
# queue_url = 'https://sqs.eu-west-1.amazonaws.com/712531873081/CoffeeOrderQueue.fifo'
queue_url = "https://sqs.eu-west-1.amazonaws.com/712531873081/CoffeeOrderQueueStandart"
sns_topic_arn_base = "arn:aws:sns:eu-west-1:712531873081:drink-order-topic-for-"

logger = Logger()


@app.get("/")
@tracer.capture_method
def index():
    with open("index.html") as f:
        return {"message": f.read()}


@app.get("/hello")
@tracer.capture_method
def hello():
    return {"message": "Hello world!"}


@app.post("/")
@tracer.capture_method
def submit_order():
    event = app.current_event
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
    except botocore.exceptions.ClientError as e:
        logger.exception(e)
        # You need to create the topic and subsribe the email here
        return {
            "statusCode": 200,
            "body": json.dumps(
                "Please confirm your email and then resubmit your drink"
            ),
        }

    messageToSQS = {"name": name, "email": email, "drink": drink}

    sqs.send_message(QueueUrl=queue_url, MessageBody=json.dumps(messageToSQS))

    return {
        "statusCode": 200,
        "body": f"""
            Thanks for the order! You will receive a message on email "{email}" when
            your drink is ready. Your order: "{drink}" for "{name}"
        """,
    }


@tracer.capture_lambda_handler
@logger.inject_lambda_context(
    correlation_id_path=correlation_paths.API_GATEWAY_HTTP, log_event=True
)
@metrics.log_metrics(capture_cold_start_metric=True)
def lambda_handler(event, context):
    try:
        return app.resolve(event, context)
    except Exception as e:
        logger.exception(e)
        raise
