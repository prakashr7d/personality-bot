import click
from dash_ecomm.constants import PRODUCT_EXCEL_SHEET, PRODUCTS_JSON
from dash_ecomm.database_utils import get_products_to_json, upload_data_to_elastic
from elasticsearch import Elasticsearch


@click.group()
def cli():
    pass


@cli.command(name="upload", help="uploads data onto elastic search index")
@click.option("--es-url", required=True)
@click.option("--index-name", required=True)
def upload_data(es_url, index_name):
    es = Elasticsearch(es_url)
    if es.indices.exists(index=index_name):
        es.indices.delete(index=index_name)
    get_products_to_json(PRODUCT_EXCEL_SHEET)
    upload_data_to_elastic(PRODUCTS_JSON, es)


@cli.command(name="show", help="shows laptops name from elastic search")
@click.option("--es-url", required=True)
@click.option("--index-name", required=True)
def show_data(es_url, index_name):
    query = {
        "_source": [],
        "size": 5,
        "query": {
            "bool": {
                "filter": [
                    {"multi_match": {"query": "laptops", "fields": ["sub_category"]}}
                ]
            }
        },
    }
    es = Elasticsearch(es_url)
    products = es.search(index=index_name, body=query, scroll="1m")
    for i in products["hits"]["hits"]:
        print(i["_source"]["brand"])


if __name__ == "__main__":
    cli()
