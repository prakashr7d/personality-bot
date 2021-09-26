import datetime
from datetime import datetime, timedelta  # noqa:  F811
from typing import Any, Dict, List, Text

from dash_ecomm.constants import (
    CANCEL_ORDER,
    ORDER_COLUMN_IMAGE_URL,
    ORDER_COLUMN_PRODUCT_NAME,
    ORDER_COLUMN_STATUS,
    ORDER_STATUS,
    PRODUCT_DETAILS,
)


def get_unblock_timestamp(after_n_minutes: int = 2) -> datetime:
    now = datetime.now()
    delta = timedelta(minutes=after_n_minutes)
    unblock_timestamp = now + delta
    return unblock_timestamp


def get_feedback_timestamp(after_n_minutes: int = 2) -> datetime:
    now = datetime.now()
    delta = timedelta(seconds=after_n_minutes)
    feedback_timestamp = now + delta
    return feedback_timestamp


def add_track_item_button(
    order: Dict[Text, Any], carousel: Dict[Text, Any]
) -> Dict[Text, Any]:
    carousel["buttons"].append(
        {"title": ORDER_STATUS, "payload": "", "type": "postback"}
    )


def create_order_carousel(orders: List[Dict[Text, Any]]) -> Dict[Text, Any]:
    carousel = {
        "type": "template",
        "payload": {"template_type": "generic", "elements": []},
    }
    for selected_order in orders:
        carousel_element = {
            "title": selected_order[ORDER_COLUMN_PRODUCT_NAME],
            "subtitle": f"Status: {selected_order[ORDER_COLUMN_STATUS]}",
            "image_url": selected_order[ORDER_COLUMN_IMAGE_URL],
            "buttons": [
                {
                    "title": PRODUCT_DETAILS,
                    "payload": "",
                    "type": "postback",
                },
                {
                    "title": CANCEL_ORDER,
                    "payload": "",
                    "type": "postback",
                },
            ],
        }
        add_track_item_button(selected_order, carousel_element)
        carousel["payload"]["elements"].append(carousel_element)
    return carousel
