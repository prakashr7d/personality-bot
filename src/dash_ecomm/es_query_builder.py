import logging
import os
from typing import Dict, Text

from elasticsearch import Elasticsearch

logger = logging.getLogger(__name__)


def range_filter_under(price_min: int, products):
    filtered_product = []

    for selected_product in products:
        product = selected_product["_source"]
        if product["price"] < price_min:
            filtered_product.append(selected_product)


class EsQueryBuilder:
    def __init__(self):
        self.es = Elasticsearch(os.environ.get("ELASTICSEARCH_URL"))

    def product_search_with_id(self, product_id):
        query = {
            "_source": [],
            "query": {
                "bool": {
                    "filter": [
                        {"multi_match": {"query": product_id, "fields": ["_id"]}}
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=query)
        return products

    def product_search_with_scroll(self, scroll_id):
        products = self.es.scroll(scroll_id=scroll_id, scroll="1m")
        return products

    def product_search_with_sub_category(self, category: Text):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "fuzzy": {"sub_category": {"value": f"{category}", "fuzziness": 10}},
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_sub_category_with_max(self, category: Text, price_max: int):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{category}",
                                "type": "best_fields",
                                "fields": ["category", "sub_category"],
                                "operator": "and",
                            }
                        },
                        {"range": {"price": {"lte": price_max}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_category(self, category: Text):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {"fuzzy": {"category": {"value": f"{category}", "fuzziness": 10}}},
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_category_and_max_price(
        self, price_max: int, category: Text
    ):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{category}",
                                "type": "best_fields",
                                "fields": ["category", "sub_category"],
                                "operator": "and",
                            }
                        },
                        {"range": {"price": {"lte": price_max}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_price(
        self, message: Text, price_min: int, price_max: int
    ) -> (Dict, int):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": message,
                                "type": "best_fields",
                                "fields": ["category", "sub_category"],
                                "operator": "or",
                            }
                        },
                        {"range": {"price": {"gte": price_min, "lte": price_max}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        # count = self.es.count(index="e_comm", body=product_search)
        return products

    def product_search_with_price_max(
        self, message: Text, price_max: int
    ) -> (Dict, int):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{message}",
                                "fields": ["category", "sub_category"],
                                "operator": "or",
                            }
                        },
                        {"range": {"price": {"lte": price_max}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        # count = self.es.count(index="e_comm", body=product_search)
        return products

    def product_search_with_price_min(
        self, message: Text, price_min: int
    ) -> (Dict, int):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": message,
                                "type": "best_fields",
                                "fields": ["category", "sub_category"],
                                "operator": "or",
                            }
                        },
                        {"range": {"price": {"gte": price_min}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_colors(self, message: Text) -> Dict:
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{message}",
                                "fields": ["sub_category", "color"],
                                "operator": "and",
                            }
                        }
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_brand(self, brand: Text) -> (Dict, int):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{brand}",
                                "fields": ["brand"],
                                "operator": "or",
                            }
                        }
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_brand_and_max(
        self, price_max: int, brand: Text
    ) -> (Dict, int):
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{brand}",
                                "fields": ["brand"],
                                "operator": "or",
                            }
                        },
                        {"range": {"price": {"lte": price_max}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_gender(self, message: Text) -> Dict:
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": f"{message}",
                                "fields": ["sub_category", "gender"],
                                "operator": "or",
                            }
                        }
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products

    def product_search_with_all(
        self, message: Text, price_min: int, price_max: int
    ) -> Dict:
        product_search = {
            "_source": [],
            "size": 5,
            "query": {
                "bool": {
                    "filter": [
                        {
                            "multi_match": {
                                "query": message,
                                "fields": [
                                    "category",
                                    "sub_category",
                                    "brand",
                                    "gender",
                                    "color",
                                ],
                                "operator": "and",
                            }
                        },
                        {"range": {"price": {"gte": price_min, "lte": price_max}}},
                    ]
                }
            },
        }
        products = self.es.search(index="e_comm", body=product_search, scroll="1m")
        return products
