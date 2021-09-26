import json
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Text

import numpy as np
import pandas as pd
import yaml
from dash_ecomm.constants import (
    DB_FILE,
    DB_USER_COLUMN,
    DB_USER_ORDERS,
    DELIVERED,
    ORDER_COLUMN_EMAIL,
    ORDER_COLUMN_ID,
    ORDER_COLUMN_REFUNDED,
    ORDER_COLUMN_RETURNABLE,
    ORDER_COLUMN_STATUS,
    USER_PROFILE_COLUMN_EMAIL,
    USER_PROFILE_COLUMN_FIRSTNAME,
    USER_PROFILE_COLUMN_ID,
    USER_PROFILE_COLUMN_LASTNAME,
    USER_PROFILE_COLUMN_OTP,
    this_path,
)
from elasticsearch import Elasticsearch

with open(DB_FILE, "r") as dbf:
    DATABASE = yaml.safe_load(dbf)

logger = logging.getLogger(__name__)


@dataclass
class UserProfile:
    email: Text
    user_id: int
    first_name: Text
    last_name: Text
    otp: int


@dataclass
class Order:
    order_date: str
    order_number: int
    order_email: Text
    name: Text
    color: Text
    size: Text
    status: Text
    image_url: Text


def get_all_orders_from_email(order_email: Text) -> List[Dict[Text, Any]]:
    global DATABASE

    orders = []
    for order in DATABASE[DB_USER_ORDERS]:
        if order[ORDER_COLUMN_EMAIL] == order_email:
            orders.append(order)

    return orders


def get_order_by_order_id(order_id: int, order_email: Text):
    global DATABASE

    for order in DATABASE[DB_USER_ORDERS]:
        if (
            order[ORDER_COLUMN_ID] == order_id
            and order[ORDER_COLUMN_EMAIL] == order_email
        ):
            return order
    return False


def is_valid_user(useremail: Text) -> bool:
    global DATABASE

    is_valid_user = False

    if useremail in DATABASE[DB_USER_COLUMN]:
        is_valid_user = True

    return is_valid_user


def is_valid_otp(otp: Text, useremail: Text) -> bool:
    global DATABASE
    valid_otp = False
    if useremail in DATABASE[DB_USER_COLUMN]:
        if str(otp) == DATABASE[DB_USER_COLUMN][useremail][USER_PROFILE_COLUMN_OTP]:
            valid_otp = True
    return valid_otp


def get_user_info_from_db(useremail: Text) -> UserProfile:
    global DATABASE

    if useremail not in DATABASE[DB_USER_COLUMN]:
        raise ValueError(f"Useremail {useremail} not found in database")

    profile_info = DATABASE[DB_USER_COLUMN][useremail]
    return UserProfile(
        user_id=profile_info[USER_PROFILE_COLUMN_ID],
        email=profile_info[USER_PROFILE_COLUMN_EMAIL],
        first_name=profile_info[USER_PROFILE_COLUMN_FIRSTNAME],
        last_name=profile_info[USER_PROFILE_COLUMN_LASTNAME],
        otp=profile_info[USER_PROFILE_COLUMN_OTP],
    )


def get_valid_order_count(ordermail: Text) -> int:
    global DATABASE

    order_count = 0
    orders = get_all_orders_from_email(ordermail)
    for selected_order in orders:
        if selected_order[ORDER_COLUMN_EMAIL] == ordermail:
            order_count += 1
    return order_count


def get_valid_order_return(ordermail: Text) -> List[Dict[Text, Any]]:
    global DATABASE

    delivered_order = []
    orders = get_all_orders_from_email(ordermail)
    for selected_order in orders:
        if (
            selected_order[ORDER_COLUMN_STATUS] == DELIVERED
            and selected_order[ORDER_COLUMN_RETURNABLE]
        ):
            delivered_order.append(selected_order)
    return delivered_order


def validate_order_id(order_id: Text, order_email: Text) -> bool:
    global DATABASE

    for selected_order in DATABASE[DB_USER_ORDERS]:
        if (
            order_id in selected_order[ORDER_COLUMN_ID]
            and order_email == selected_order[ORDER_COLUMN_EMAIL]
        ):
            return True


def update_order_status(status: Text, order_id: Text):
    global DATABASE

    for selected_order in DATABASE[DB_USER_ORDERS]:
        if order_id in selected_order[ORDER_COLUMN_ID]:
            selected_order[ORDER_COLUMN_STATUS] = status
            selected_order[ORDER_COLUMN_RETURNABLE] = False
            selected_order[ORDER_COLUMN_REFUNDED] = False
    # with open(DB_FILE, "w+") as dbfw:
    #     yaml.dump(DATABASE, dbfw)


def upload_data_to_elastic(file_path: Text, es_client: Elasticsearch):
    with open(this_path.parent / file_path) as products:
        content = json.load(products)
        print(es_client)
        for item in content["data"]:
            es_client.index(
                index="e_comm", id=item["id"], doc_type="products", body=item
            )


def get_products_to_json(excel_file_path: Text):
    products = pd.read_excel(
        this_path.parent / excel_file_path,
        usecols="A:M",
        dtype={
            "ratings_count": np.int,
            "price": np.int,
            "color": np.str,
            "gender": np.str,
            "image": np.str,
        },
    )
    products = products.replace(np.nan, "", regex=True)
    products_json = {}
    products_list = []
    for per_dict in products.to_dict(orient="records"):
        products_list.append(per_dict)
    products_json["data"] = products_list
    with open(this_path.parent / "products.json", "w+") as products_json_file:
        json.dump(products_json, products_json_file)


def validate_return_order(order_id, order_email):
    global DATABASE
    returnable = False
    for selected_order in DATABASE[DB_USER_ORDERS]:
        if (
            order_email in selected_order[ORDER_COLUMN_EMAIL]
            and order_id in selected_order[ORDER_COLUMN_ID]
        ):
            if selected_order[ORDER_COLUMN_RETURNABLE]:
                returnable = True
    return returnable
