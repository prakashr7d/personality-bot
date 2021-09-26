import json
from datetime import datetime

import click
import pika
from elasticsearch import Elasticsearch

es = None


def _callback(channel, method, properties, body):
    global es
    event = json.loads(body)
    if event["event"] in ["user", "bot", "action", "followup"]:
        event["@timestamp"] = datetime.now()
        es.index(index="rasa-index", body=event)


@click.command()
@click.option("--rmq-username", default="guest")
@click.option("--rmq-password", default="guest")
@click.option("--rmq-queue-name", default="es-queue")
@click.option("--rmq-host", default="localhost")
@click.option("--es-host", default="http://localhost:9200/")
@click.option("--rmq-port", default=5672)
def run_consumer(
    rmq_username, rmq_password, rmq_queue_name, rmq_host, es_host, rmq_port
):
    global es
    es = Elasticsearch(es_host)
    credentials = pika.PlainCredentials(rmq_username, rmq_password)
    connection = pika.BlockingConnection(
        pika.ConnectionParameters(host=rmq_host, port=rmq_port, credentials=credentials)
    )
    # start consumption of channel
    channel = connection.channel()
    channel.basic_consume(rmq_queue_name, _callback, auto_ack=True)
    channel.start_consuming()


if __name__ == "__main__":
    run_consumer()
