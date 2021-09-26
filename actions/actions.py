import logging
from typing import Any, Dict, List, Text, Tuple

from dash_ecomm import generic_utils
from dash_ecomm.constants import (
    ACTION_CANCEL_ORDER,
    ACTION_CHECK_ALL_ORDERS,
    ACTION_PRODUCT_INQUIRY,
    ACTION_RETURN_ORDER,
    ACTION_THAT_TRIGGERED_SHOW_MORE,
    ADD_TO_CART,
    BRAND,
    BUTTONS,
    BUY_NOW,
    CANCEL_ORDER,
    CANCELED,
    CATEGORY,
    COLOR,
    CREDIT_POINTS,
    DELIVERED,
    DONT_NEED_THE_PRODUCT,
    ELEMENTS,
    EMAIL_TRIES,
    ENTITY_NAMES,
    FORM_SLOTS,
    GENDER,
    GENERIC,
    IMAGE_URL,
    INCORRECT_ITEMS,
    IS_LOGGED_IN,
    IS_SHOW_MORE_TRIGGERED,
    LOGIN_BLOCKED,
    MAX,
    MAX_EMAIL_TRIES,
    MAX_ITEM_IN_CAROUSEL,
    MAX_OTP_TRIES,
    MIN,
    MIN_ITEM_IN_CAROUSEL,
    MIN_NUMBER_ZERO,
    NOT_PICKED,
    ORDER_COLUMN_EMAIL,
    ORDER_COLUMN_ID,
    ORDER_COLUMN_IMAGE_URL,
    ORDER_COLUMN_PRODUCT_ID,
    ORDER_COLUMN_PRODUCT_NAME,
    ORDER_COLUMN_RETURNABLE,
    ORDER_COLUMN_STATUS,
    ORDER_CONFIRMED,
    ORDER_ID_FOR_RETURN,
    ORDER_PENDING,
    ORDER_STATUS,
    OTP_TRIES,
    PAYLOAD,
    PAYLOAD_BUTTON_BLOCKED,
    PICKED,
    PICKUP_ADDRESS_FOR_RETURN,
    POSTBACK,
    PRICE_MAX,
    PRICE_MIN,
    PRIMARY_ACCOUNT,
    PRODUCT_DETAILS,
    PRODUCT_NAME,
    QUALITY_ISSUES,
    REASON_FOR_RETURN,
    REASON_FOR_RETURN_DESCRIPTION,
    RECEIVED,
    REFUND_ACCOUNT,
    REFUNDED,
    REPLACE_ORDER,
    REPLACE_PRODUCT,
    REQUESTED_SLOT,
    RETURN_ORDER,
    RETURN_ORDER_FORM,
    RETURN_PRODUCT,
    SCROLL_ID,
    SHIPPED,
    SHOW_MORE_COUNT,
    STOP_SHOW_MORE_COUNT,
    SUB_CATEGORY,
    SUBTITLE,
    TEMPLATE,
    TEMPLATE_TYPE,
    TITLE,
    TYPE,
    TYPE_OF_RETURN,
    USER_EMAIL,
    USER_FIRST_NAME,
    USER_LAST_NAME,
    USER_OTP,
)
from dash_ecomm.database_utils import (
    get_all_orders_from_email,
    get_order_by_order_id,
    get_user_info_from_db,
    get_valid_order_count,
    get_valid_order_return,
    is_valid_otp,
    is_valid_user,
    validate_return_order,
)
from dash_ecomm.es_query_builder import EsQueryBuilder
from rasa_sdk import Action, FormValidationAction, Tracker, events
from rasa_sdk.events import (
    ActiveLoop,
    AllSlotsReset,
    EventType,
    FollowupAction,
    SlotSet,
)
from rasa_sdk.executor import CollectingDispatcher

logger = logging.getLogger(__name__)


class PersonalGreet(Action):
    def name(self) -> Text:
        return "personal_greet"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        is_logged_in, user_profile_slot_sets, utter = self.__is_logged_in_user(tracker)
        dispatcher.utter_message(**utter)
        return user_profile_slot_sets

    @staticmethod
    def __get_useremail_from_token(token) -> Text:
        # When we have JWT then write the JWT decode logic here
        return token

    @staticmethod
    def validate_user(useremail: Text):
        user_profile = None
        if is_valid_user(useremail):
            user_profile = get_user_info_from_db(useremail)
        return user_profile

    def __get_user_token_from_metadata(self, tracker: Tracker) -> Text:
        user_token = None
        tracker_events = tracker.current_state()["events"]
        user_events = []
        for e in tracker_events:
            if e["event"] == "user":
                user_events.append(e)
        if tracker.events:
            user_token = user_events[-1]["metadata"].get("user_token", None)
        return user_token

    def __is_logged_in_user(
        self, tracker: Tracker
    ) -> Tuple[bool, List[SlotSet], Dict[Text, Text]]:
        is_logged_in = tracker.get_slot("is_logged_in")
        slot_set = []
        utter = {"template": "utter_generic_greet"}
        if not is_logged_in:
            token = self.__get_user_token_from_metadata(tracker)
            if token:
                user_email = self.__get_useremail_from_token(token)
                user_profile = self.validate_user(user_email)
                if user_profile:
                    slot_set += [
                        SlotSet(key=USER_EMAIL, value=user_profile.email),
                        SlotSet(key=USER_FIRST_NAME, value=user_profile.first_name),
                        SlotSet(key=USER_LAST_NAME, value=user_profile.last_name),
                        SlotSet(key=IS_LOGGED_IN, value=True),
                        SlotSet(key=USER_OTP, value=user_profile.otp),
                    ]
                    utter = {
                        "template": "utter_personalized_greet_new_session",
                        "first_name": user_profile.first_name,
                    }
                else:
                    slot_set += self.__empty_user_slots()
                    logging.info(
                        "User has logged in to the website but "
                        "email is not present in our database"
                    )
            else:
                slot_set += self.__empty_user_slots()
                logging.info("User has not logged in")
        else:
            logging.info("User has logged in")
            utter = {
                "template": "utter_personalized_greet_new_session",
                "first_name": tracker.get_slot(USER_FIRST_NAME),
            }

        return is_logged_in, slot_set, utter

    def __empty_user_slots(self):
        slot_set = [
            SlotSet(key=USER_EMAIL, value=None),
            SlotSet(key=USER_FIRST_NAME, value=None),
            SlotSet(key=USER_LAST_NAME, value=None),
            SlotSet(key=IS_LOGGED_IN, value=False),
            SlotSet(key=USER_OTP, value=None),
        ]
        return slot_set


class LoginFormAction(Action):
    def name(self) -> Text:
        return "action_login_form"

    def __set_unblock_reminder(self, tracker: Tracker):
        set_reminder = True if tracker.get_slot(EMAIL_TRIES) > 0 else False

        reminder_events = []
        if set_reminder:
            logger.debug("*" * 100)
            logger.debug(set_reminder)
            timestamp = generic_utils.get_unblock_timestamp()
            login_event = events.ReminderScheduled(
                intent_name="EXTERNAL_unblock_login",
                trigger_date_time=timestamp,
                name="login_unblock",
                kill_on_user_message=False,
            )
            reminder_events.append(login_event)
        return reminder_events

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        """
        check if login blocked then
            utter login blocked
            utter you can try logining through chatbot after k minutes
            utter you can always login through website anytime
            :return set reminder unblock login after k minutes, slotset email_tries, otp_tries to 0,
        check else
          usual login prompt
        """
        login_blocked = tracker.get_slot(LOGIN_BLOCKED)
        slot_set = []
        if login_blocked:
            dispatcher.utter_message(template="utter_login_blocked")
            dispatcher.utter_message(template="utter_login_blocked_duration")
            dispatcher.utter_message(template="utter_login_via_website")

            reminder_events = self.__set_unblock_reminder(tracker)
            slot_set += [SlotSet(EMAIL_TRIES, 0), SlotSet(OTP_TRIES, 0)]
            slot_set += reminder_events
        else:
            user_email = tracker.get_slot(USER_EMAIL)
            user_profile = PersonalGreet.validate_user(user_email)
            if user_profile and not tracker.get_slot(IS_LOGGED_IN):
                dispatcher.utter_message(template="utter_login_success")
                slot_set += [
                    SlotSet(key=USER_EMAIL, value=user_profile.email),
                    SlotSet(key=USER_FIRST_NAME, value=user_profile.first_name),
                    SlotSet(key=USER_LAST_NAME, value=user_profile.last_name),
                    SlotSet(key=IS_LOGGED_IN, value=True),
                    SlotSet(key=USER_OTP, value=user_profile.otp),
                ]
            elif user_profile and tracker.get_slot(IS_LOGGED_IN):
                pass
            else:
                dispatcher.utter_message(template="utter_login_failed")
        logger.debug(slot_set)
        return slot_set


class ValidateLoginForm(FormValidationAction):
    def name(self) -> Text:
        return "validate_login_form"

    def __utter_message_and_slots(
        self, email: Text, slots: Dict[Text, Text]
    ) -> Tuple[Text, Dict]:
        slots = slots if slots else {}
        slots[USER_EMAIL] = None
        if email is None:
            utter = "utter_email_not_valid_prompt"
        elif not is_valid_user(email):
            utter = "utter_user_email_not_registered"
            slots[REQUESTED_SLOT] = None
        else:
            utter = "utter_user_email_not_valid"
        return utter, slots

    def validate_user_email(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        email_tries = tracker.get_slot(EMAIL_TRIES)
        returned_slots = {}
        if value is not None and is_valid_user(value):
            returned_slots = {USER_EMAIL: value}
        elif email_tries >= MAX_EMAIL_TRIES:
            returned_slots = {
                REQUESTED_SLOT: None,
                LOGIN_BLOCKED: True,
                USER_EMAIL: None,
            }
        else:
            email_tries += 1
            utter, returned_slots = self.__utter_message_and_slots(
                value, returned_slots
            )
            logger.debug(returned_slots)
            dispatcher.utter_message(template=utter)
            returned_slots[EMAIL_TRIES] = email_tries
        return returned_slots

    def validate_user_otp(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        email = tracker.get_slot(USER_EMAIL)
        otp_tries = tracker.get_slot(OTP_TRIES)
        if value is not None and is_valid_otp(value, email):
            logger.debug(f"{value} is a valid user")
            returned_slots = {USER_OTP: value}
        else:
            if otp_tries >= MAX_OTP_TRIES:
                returned_slots = {
                    REQUESTED_SLOT: None,
                    LOGIN_BLOCKED: True,
                    USER_OTP: None,
                }
            else:
                otp_tries += 1
                dispatcher.utter_message(template="utter_incorrect_otp")
                returned_slots = {USER_OTP: None, OTP_TRIES: otp_tries}
        return returned_slots


class ActionLoginUnblock(Action):
    def name(self) -> Text:
        return "action_unblock_login"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(template="utter_login_unblocked")
        events.ReminderCancelled(name="login_unblock")
        return [SlotSet(LOGIN_BLOCKED, False)]


class ActionLogout(Action):
    def name(self) -> Text:
        return "action_logout"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(template="utter_logout")
        return [AllSlotsReset()]


class CheckAllOrders(Action):
    def name(self) -> Text:
        return "action_check_all_orders"

    @staticmethod
    def respective_buttons(order_id, status, is_eligible, product_id):
        required_buttons = []
        payload_order_status = "order status of {}".format(order_id)
        payload_return_order = "please place the return for {}".format(order_id)

        if status == ORDER_PENDING or status == SHIPPED:
            required_buttons.append(
                {TITLE: ORDER_STATUS, PAYLOAD: payload_order_status, TYPE: POSTBACK}
            )
            required_buttons.append(
                {
                    TITLE: PRODUCT_DETAILS,
                    PAYLOAD: f"{product_id} details",
                    TYPE: POSTBACK,
                }
            )
            required_buttons.append(
                {TITLE: CANCEL_ORDER, PAYLOAD: PAYLOAD_BUTTON_BLOCKED, TYPE: POSTBACK}
            )
        elif status == DELIVERED and is_eligible:
            required_buttons.append(
                {TITLE: ORDER_STATUS, PAYLOAD: payload_order_status, TYPE: POSTBACK}
            )
            required_buttons.append(
                {TITLE: RETURN_ORDER, PAYLOAD: payload_return_order, TYPE: POSTBACK}
            )
            required_buttons.append(
                {TITLE: REPLACE_ORDER, PAYLOAD: "replace my order", TYPE: POSTBACK}
            )
            required_buttons.append(
                {
                    TITLE: PRODUCT_DETAILS,
                    PAYLOAD: f"{product_id} details",
                    TYPE: POSTBACK,
                }
            )
        else:
            required_buttons.append(
                {TITLE: ORDER_STATUS, PAYLOAD: payload_order_status, TYPE: POSTBACK}
            )
            required_buttons.append(
                {
                    TITLE: PRODUCT_DETAILS,
                    PAYLOAD: f"{product_id} details",
                    TYPE: POSTBACK,
                }
            )
        return required_buttons

    def __create_order_carousel(self, orders: List[Dict[Text, Any]]) -> Dict[Text, Any]:
        carousel = {
            TYPE: "template",
            PAYLOAD: {"template_type": "generic", "elements": []},
        }

        for selected_order in orders:
            required_buttons = self.respective_buttons(
                selected_order[ORDER_COLUMN_ID],
                selected_order[ORDER_COLUMN_STATUS],
                selected_order[ORDER_COLUMN_RETURNABLE],
                selected_order[ORDER_COLUMN_PRODUCT_ID],
            )
            if selected_order[ORDER_COLUMN_STATUS] in [NOT_PICKED, PICKED]:
                carousel_element = {
                    TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                    SUBTITLE: "Status: returning",
                    BUTTONS: required_buttons,
                    IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
                }
            elif selected_order[ORDER_COLUMN_STATUS] in [RECEIVED, REFUNDED]:
                carousel_element = {
                    TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                    SUBTITLE: "Status: returned",
                    BUTTONS: required_buttons,
                    IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
                }
            else:
                carousel_element = {
                    TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                    SUBTITLE: f"Status: {selected_order[ORDER_COLUMN_STATUS]}",
                    IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
                    BUTTONS: required_buttons,
                }
            carousel[PAYLOAD]["elements"].append(carousel_element)
        return carousel

    def __get_current_orders(
        self, no_of_valid_orders: int, order_email: Text, orders: List[Dict[Text, Any]]
    ) -> (List[Dict[Text, Any]], int):
        valid_orders = []
        minimum_order_index = MIN_ITEM_IN_CAROUSEL
        maximum_order_index = MIN_ITEM_IN_CAROUSEL
        if no_of_valid_orders < MAX_ITEM_IN_CAROUSEL:
            minimum_order_index = MIN_ITEM_IN_CAROUSEL
            maximum_order_index = no_of_valid_orders
            no_of_valid_orders = STOP_SHOW_MORE_COUNT
        else:
            minimum_order_index = no_of_valid_orders - MAX_ITEM_IN_CAROUSEL
            maximum_order_index = no_of_valid_orders
            no_of_valid_orders -= MAX_ITEM_IN_CAROUSEL
        for selected_order in orders[minimum_order_index:maximum_order_index]:
            if selected_order[ORDER_COLUMN_EMAIL] == order_email:
                valid_orders.append(selected_order)
        return valid_orders, no_of_valid_orders

    def __validate_orders(
        self,
        valid_orders: List[Dict[Text, Any]],
        no_of_valid_orders: int,
        dispatcher: CollectingDispatcher,
        is_show_more_triggered: bool,
    ) -> (List[Any]):
        slot_set = []
        if not valid_orders:
            dispatcher.utter_message(template="utter_no_open_orders")
        else:
            if is_show_more_triggered:
                dispatcher.utter_message(template="utter_on_show_orders")
            else:
                dispatcher.utter_message(template="utter_open_current_orders")
            carousel_order = self.__create_order_carousel(valid_orders)
            dispatcher.utter_message(attachment=carousel_order)
            if no_of_valid_orders > STOP_SHOW_MORE_COUNT:
                dispatcher.utter_message(template="utter_show_more_option")
                slot_set.append(
                    SlotSet(ACTION_THAT_TRIGGERED_SHOW_MORE, ACTION_CHECK_ALL_ORDERS)
                )
            else:
                slot_set.append(SlotSet(ACTION_THAT_TRIGGERED_SHOW_MORE, None))
        return slot_set

    def run(
        self,
        dispatcher: CollectingDispatcher,
        tracker: Tracker,
        domain: Dict[Text, Any],
    ) -> List[SlotSet]:
        order_email = tracker.get_slot(USER_EMAIL)
        show_more_count = tracker.get_slot(SHOW_MORE_COUNT)
        is_show_more_triggered = tracker.get_slot(IS_SHOW_MORE_TRIGGERED)
        valid_orders = []
        no_of_valid_orders = MIN_NUMBER_ZERO
        orders = get_all_orders_from_email(order_email)
        if not is_show_more_triggered:
            no_of_valid_orders = get_valid_order_count(order_email)
        else:
            if show_more_count is None or show_more_count < MIN_NUMBER_ZERO:
                no_of_valid_orders = get_valid_order_count(order_email)
            else:
                no_of_valid_orders = show_more_count

        valid_orders, no_of_valid_orders = self.__get_current_orders(
            no_of_valid_orders, order_email, orders
        )
        slot_set = self.__validate_orders(
            valid_orders, no_of_valid_orders, dispatcher, is_show_more_triggered
        )
        slot_set.append(SlotSet(SHOW_MORE_COUNT, no_of_valid_orders))
        slot_set.append(SlotSet(IS_SHOW_MORE_TRIGGERED, False))
        return slot_set


class ShowMoreAction(Action):
    def name(self) -> Text:
        return "show_more_action"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        followup_action = []
        action_triggered = tracker.get_slot(ACTION_THAT_TRIGGERED_SHOW_MORE)
        if action_triggered in [
            ACTION_CHECK_ALL_ORDERS,
            ACTION_RETURN_ORDER,
            ACTION_CANCEL_ORDER,
            ACTION_PRODUCT_INQUIRY,
        ]:
            followup_action.append(FollowupAction(action_triggered))
            followup_action.append(SlotSet(IS_SHOW_MORE_TRIGGERED, True))
        else:
            dispatcher.utter_message(template="utter_show_more_something")
            followup_action.append(SlotSet(IS_SHOW_MORE_TRIGGERED, False))
        return followup_action


class ActionOrderStatus(Action):
    def name(self) -> Text:
        return "action_order_status"

    def __create_order_carousel(
        self, selected_order: List[Dict[Text, Any]]
    ) -> Dict[Text, Any]:
        carousel = {
            TYPE: "template",
            PAYLOAD: {"template_type": "generic", "elements": []},
        }
        if selected_order[ORDER_COLUMN_STATUS] in [NOT_PICKED, PICKED]:
            carousel_element = {
                TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                SUBTITLE: f"Status: returning - {selected_order[ORDER_COLUMN_STATUS]}",
                BUTTONS: [],
                IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
            }
        elif selected_order[ORDER_COLUMN_STATUS] in [RECEIVED, REFUNDED]:
            carousel_element = {
                TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                SUBTITLE: f"Status: returned - {selected_order[ORDER_COLUMN_STATUS]}",
                BUTTONS: [],
                IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
            }
        else:
            carousel_element = {
                TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                SUBTITLE: f"Status: {selected_order[ORDER_COLUMN_STATUS]}",
                BUTTONS: [],
                IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
            }
        carousel[PAYLOAD]["elements"].append(carousel_element)
        return carousel

    @staticmethod
    def template_for_order_status(status_for_order_id):
        if status_for_order_id == ORDER_PENDING:
            template = "utter_order_status_order_pending"
        elif status_for_order_id == ORDER_CONFIRMED:
            template = "utter_order_status_order_confirmed"
        elif status_for_order_id == SHIPPED:
            template = "utter_order_status_order_shipped"
        elif status_for_order_id == CANCELED:
            template = "utter_order_status_cancelled"
        elif status_for_order_id == DELIVERED:
            template = "utter_order_status_delivered"
        elif status_for_order_id == NOT_PICKED:
            template = "utter_order_status_not_picked"
        elif status_for_order_id == PICKED:
            template = "utter_order_status_picked"
        elif status_for_order_id == RECEIVED:
            template = "utter_order_status_received"
        elif status_for_order_id == REFUNDED:
            template = "utter_order_status_refunded"
        else:
            template = "utter_order_status_failed"
        return template

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:

        follow_up_action = []
        order_email = tracker.get_slot(USER_EMAIL)
        is_logged_in = tracker.get_slot(IS_LOGGED_IN)
        if is_logged_in:
            if not tracker.latest_message["entities"]:
                follow_up_action.append(FollowupAction(ACTION_CHECK_ALL_ORDERS))
                return follow_up_action
            else:
                order_id_to_show_order_status = tracker.latest_message["entities"][0][
                    "value"
                ]
                follow_up_action.append(FollowupAction("utter_anything_else"))
                logger.info(order_id_to_show_order_status)
                order_for_order_id = get_order_by_order_id(
                    order_id_to_show_order_status, order_email
                )
                if order_for_order_id:
                    valid_order = order_for_order_id
                    carousel_order = self.__create_order_carousel(valid_order)
                    status_for_order_id = order_for_order_id[ORDER_COLUMN_STATUS]
                    template = self.template_for_order_status(status_for_order_id)
                    if template != "utter_order_status_failed":
                        dispatcher.utter_message(attachment=carousel_order)
                    utter = {
                        "template": template,
                        "order_id": order_id_to_show_order_status,
                        "small_order_id": order_id_to_show_order_status.lower(),
                        "shipped_date": "04/04/2021",
                        "delivery_date": "10/05/2021",
                        "status": status_for_order_id,
                    }
                    dispatcher.utter_message(**utter)
                else:
                    utter = {
                        "template": "utter_order_status_failed",
                        "order_id": order_id_to_show_order_status,
                    }
                    dispatcher.utter_message(**utter)

                return follow_up_action
        else:
            dispatcher.utter_message(template="utter_try_after_logged_in")
            return []


class ShowValidReturnOrders(Action):
    def name(self) -> Text:
        return "action_show_valid_return_order"

    def __create_order_carousel(
        self, delivered_orders: List[Dict[Text, Any]]
    ) -> Dict[Text, Any]:
        carousel = {
            TYPE: "template",
            PAYLOAD: {"template_type": "generic", "elements": []},
        }
        for selected_order in delivered_orders:
            carousel_element = {
                TITLE: selected_order[ORDER_COLUMN_PRODUCT_NAME],
                SUBTITLE: f"Status: {selected_order[ORDER_COLUMN_STATUS]}",
                IMAGE_URL: selected_order[ORDER_COLUMN_IMAGE_URL],
                BUTTONS: [
                    {
                        TITLE: RETURN_ORDER,
                        PAYLOAD: f"please place a return for {selected_order[ORDER_COLUMN_ID]}",
                        TYPE: POSTBACK,
                    },
                    {
                        TITLE: REPLACE_ORDER,
                        PAYLOAD: "replace my order",
                        TYPE: POSTBACK,
                    },
                ],
            }
            carousel[PAYLOAD]["elements"].append(carousel_element)
        return carousel

    def __get_current_order(
        self,
        no_of_valid_orders: int,
        valid_orders: List[Dict[Text, Any]],
        user_mail: Text,
    ):
        carsousel_orders = []
        minimum_order_index = MIN_ITEM_IN_CAROUSEL
        maximum_order_index = MIN_ITEM_IN_CAROUSEL
        if no_of_valid_orders < MAX_ITEM_IN_CAROUSEL:
            minimum_order_index = MIN_ITEM_IN_CAROUSEL
            maximum_order_index = no_of_valid_orders
            no_of_valid_orders = STOP_SHOW_MORE_COUNT
        else:
            minimum_order_index = no_of_valid_orders - MAX_ITEM_IN_CAROUSEL
            maximum_order_index = no_of_valid_orders
            no_of_valid_orders -= MAX_ITEM_IN_CAROUSEL
        for selected_order in valid_orders[minimum_order_index:maximum_order_index]:
            carsousel_orders.append(selected_order)
        return carsousel_orders, no_of_valid_orders

    def __validate_orders(
        self,
        valid_orders: List[Dict[Text, Any]],
        no_of_valid_orders: int,
        dispatcher: CollectingDispatcher,
        is_show_more_triggered: bool,
    ) -> (List[Any]):
        slot_set = []
        if not valid_orders:
            dispatcher.utter_message(template="utter_no_open_orders")
        else:
            if is_show_more_triggered:
                dispatcher.utter_message(template="utter_orders_return_show_more")
            else:
                dispatcher.utter_message(template="utter_orders_eligible_for_return")
            carousel_order = self.__create_order_carousel(valid_orders)
            dispatcher.utter_message(attachment=carousel_order)
            if no_of_valid_orders > STOP_SHOW_MORE_COUNT:
                dispatcher.utter_message(template="utter_show_more_option")
                slot_set.append(
                    SlotSet(ACTION_THAT_TRIGGERED_SHOW_MORE, ACTION_RETURN_ORDER)
                )
            else:
                slot_set.append(SlotSet(ACTION_THAT_TRIGGERED_SHOW_MORE, None))
        return slot_set

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        user_mail = tracker.get_slot(USER_EMAIL)
        show_more_count = tracker.get_slot(SHOW_MORE_COUNT)
        is_show_more_triggered = tracker.get_slot(IS_SHOW_MORE_TRIGGERED)
        valid_orders = get_valid_order_return(user_mail)
        no_of_valid_orders = 0
        if not is_show_more_triggered:
            no_of_valid_orders = len(valid_orders)
        else:
            if show_more_count is None or show_more_count < MIN_NUMBER_ZERO:
                no_of_valid_orders = len(valid_orders)
            else:
                no_of_valid_orders = show_more_count
        valid_orders, no_of_valid_orders = self.__get_current_order(
            no_of_valid_orders, valid_orders, user_mail
        )
        slot_set = self.__validate_orders(
            valid_orders, no_of_valid_orders, dispatcher, is_show_more_triggered
        )
        slot_set.append(SlotSet(SHOW_MORE_COUNT, no_of_valid_orders))
        slot_set.append(SlotSet(IS_SHOW_MORE_TRIGGERED, False))
        return slot_set


class ReturnOrderAction(Action):
    def name(self) -> Text:
        return "action_return_order"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        order_id = tracker.get_slot(ORDER_ID_FOR_RETURN)
        pickup_address_for_return = tracker.get_slot(PICKUP_ADDRESS_FOR_RETURN)
        dispatcher.utter_message(
            template="utter_return_initiated",
            order_no=order_id,
            address=pickup_address_for_return,
        )
        return [
            SlotSet(ORDER_ID_FOR_RETURN, None),
            SlotSet(REASON_FOR_RETURN, None),
            SlotSet(REASON_FOR_RETURN_DESCRIPTION, None),
            SlotSet(TYPE_OF_RETURN, None),
            SlotSet(PICKUP_ADDRESS_FOR_RETURN, None),
            SlotSet(REFUND_ACCOUNT, None),
        ]


class ValidateReturnOrder(FormValidationAction):
    def name(self) -> Text:
        return "validate_return_order_form"

    def validate_order_id_for_return(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        slot_set = {}
        if value is not None and value in [RETURN_PRODUCT]:
            slot_set = {ORDER_ID_FOR_RETURN: value}
        else:
            dispatcher.utter_message(template="utter_ineligible_order_id")
            slot_set = {REQUESTED_SLOT: ORDER_ID_FOR_RETURN}
        return [slot_set]

    def validate_return_a_reason(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        slot_set = {}
        if value is not None:
            if value in [QUALITY_ISSUES, INCORRECT_ITEMS, DONT_NEED_THE_PRODUCT]:
                slot_set = {
                    REASON_FOR_RETURN: value,
                    REQUESTED_SLOT: REASON_FOR_RETURN_DESCRIPTION,
                }
        else:
            dispatcher.utter_message(template="utter_invalid_reason")
            slot_set = {REQUESTED_SLOT: REASON_FOR_RETURN}
        return [slot_set]

    def validate_return_e_type(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        slot_set = {}
        if value is not None:
            slot_set = {TYPE_OF_RETURN: value}
        else:
            slot_set = {REQUESTED_SLOT: TYPE_OF_RETURN}
            if value in [REPLACE_PRODUCT]:
                dispatcher.utter_message(template="utter_replace_order_inprogress")
            else:
                dispatcher.utter_message(template="utter_invalid_type_of_return")
        return [slot_set]

    def validate_return_a_reason_description(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        slot_set = {}
        if value is not None:
            slot_set = {REASON_FOR_RETURN_DESCRIPTION: value}
        else:
            slot_set = {REQUESTED_SLOT: REASON_FOR_RETURN_DESCRIPTION}
        return [slot_set]

    def validate_return_pickup_address(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        slot_set = {}
        order_email = tracker.get_slot("user_email")
        if value is not None and validate_return_order(value, order_email):
            slot_set = {PICKUP_ADDRESS_FOR_RETURN: value}
        else:
            slot_set = {REQUESTED_SLOT: PICKUP_ADDRESS_FOR_RETURN}
        return [slot_set]

    def validate_return_refund_account(
        self,
        value: Text,
        dispatcher: "CollectingDispatcher",
        tracker: "Tracker",
        domain: "DomainDict",  # noqa: F821
    ) -> List[EventType]:
        slot_set = {}
        if value is not None and value.lower() in [PRIMARY_ACCOUNT, CREDIT_POINTS]:
            slot_set = {REFUND_ACCOUNT: value}
        else:
            slot_set = {REQUESTED_SLOT: REFUND_ACCOUNT}
        return [slot_set]


class ActionAskSwitch(Action):
    def name(self) -> Text:
        return "action_switch"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        active_form = tracker.active_loop.get("name")
        slot_set = []
        if active_form in [RETURN_ORDER_FORM]:
            for slot in FORM_SLOTS[active_form]:
                slot_set.append(SlotSet(slot, None))
        slot_set.append(ActiveLoop(None))
        slot_set.append(SlotSet(REQUESTED_SLOT, None))
        return slot_set


class ActionProductInquiry(Action):
    def name(self) -> Text:
        return "action_product_inquiry"

    def __validate_entities(
        self,
        category,
        sub_category,
        color: Text = None,
        gender: Text = None,
        price_min: int = None,
        price_max: int = None,
        brand: Text = None,
        scroll_id: Text = None,
    ) -> Dict:
        not_none_entities = {}
        entities = [
            category,
            sub_category,
            color,
            price_max,
            gender,
            price_min,
            brand,
            scroll_id,
        ]
        for entity in range(0, len(entities)):
            if entities[entity] is not None:
                not_none_entities[ENTITY_NAMES[entity]] = entities[entity]
        logger.info(not_none_entities)
        return not_none_entities

    def __price_queries(
        self, not_non_entities: Dict, entities_present: list, message: Text
    ) -> (Dict, int):
        products = None
        query_builder = EsQueryBuilder()
        if PRICE_MIN in entities_present and PRICE_MAX in entities_present:
            products = query_builder.product_search_with_price(
                message,
                not_non_entities[PRICE_MIN],
                not_non_entities[PRICE_MAX],
            )
        elif PRICE_MIN in entities_present:
            products = query_builder.product_search_with_price_min(
                message, not_non_entities[PRICE_MIN]
            )
        elif PRICE_MAX in entities_present:
            products = query_builder.product_search_with_price_max(
                message, not_non_entities[PRICE_MAX]
            )
        return products

    def __not_scroll_id(  # noqa: C901
        self, not_non_entities: Dict, message: Text, entities_present, query_builder
    ) -> (Dict, int):
        products = None
        if entities_present == ENTITY_NAMES:
            logger.info("first")
            products = query_builder.product_search_with_all(
                message,
                not_non_entities[PRICE_MIN],
                not_non_entities[PRICE_MAX],
            )
        elif (
            PRICE_MIN in entities_present
            or PRICE_MAX in entities_present
            and BRAND not in entities_present
            and SUB_CATEGORY not in entities_present
            and CATEGORY not in entities_present
        ):
            products = self.__price_queries(not_non_entities, entities_present, message)
        elif (
            SUB_CATEGORY in entities_present
            and PRICE_MAX in entities_present
            and not BRAND
            and not PRICE_MIN
        ):
            products = query_builder.product_search_with_category_and_max_price(
                not_non_entities[PRICE_MAX], not_non_entities[SUB_CATEGORY]
            )
        elif (
            SUB_CATEGORY in entities_present
            and BRAND not in entities_present
            and CATEGORY not in entities_present
        ):
            products = query_builder.product_search_with_sub_category(
                not_non_entities[SUB_CATEGORY]
            )
        elif (
            SUB_CATEGORY in entities_present
            and PRICE_MAX in entities_present
            and CATEGORY not in entities_present
            and not BRAND
        ):
            products = query_builder.product_search_with_sub_category_with_max(
                not_non_entities[SUB_CATEGORY], not_non_entities[PRICE_MAX]
            )
        elif (
            CATEGORY in entities_present
            and BRAND not in entities_present
            and SUB_CATEGORY not in entities_present
        ):
            products = query_builder.product_search_with_category(
                not_non_entities[CATEGORY]
            )
        elif GENDER in entities_present and BRAND not in entities_present:
            products = query_builder.product_search_with_gender(message)
        elif BRAND in entities_present and PRICE_MAX in entities_present:
            products = query_builder.product_search_with_brand_and_max(
                not_non_entities[PRICE_MAX], not_non_entities[BRAND]
            )
        elif BRAND in entities_present:
            products = query_builder.product_search_with_brand(not_non_entities[BRAND])
        elif not entities_present:
            products = query_builder.product_search_with_category(
                not_non_entities[SUB_CATEGORY]
            )
        return products

    def __generate_query_to_elasticsearch(
        self, not_non_entities: Dict, message: Text
    ) -> (Dict, int):
        query_builder = EsQueryBuilder()
        entities_present = []
        products = None
        for entity_name in not_non_entities.keys():
            if entity_name in ENTITY_NAMES:
                entities_present.append(entity_name)
        if SCROLL_ID in not_non_entities:
            products = query_builder.product_search_with_scroll(
                not_non_entities[SCROLL_ID]
            )
        else:
            products = self.__not_scroll_id(
                not_non_entities, message, entities_present, query_builder
            )
        return products

    def __get_five_products(
        self, products, is_show_more_triggered: bool, show_more_count: int
    ):
        count = MIN_NUMBER_ZERO
        if is_show_more_triggered:
            count = show_more_count
        else:
            count = products["hits"]["total"]["value"]
        scroll_id = products["_scroll_id"]
        products = products["hits"]["hits"]
        carousel_products = []
        if count <= MAX_ITEM_IN_CAROUSEL:
            count = STOP_SHOW_MORE_COUNT
        else:
            count -= MAX_ITEM_IN_CAROUSEL
        for selected_product in products:
            carousel_products.append(selected_product)
        return carousel_products, count, scroll_id

    def __convert_response_to_carousel(self, products):
        carousel = {
            TYPE: TEMPLATE,
            PAYLOAD: {TEMPLATE_TYPE: GENERIC, ELEMENTS: []},
        }
        for selected_product in products:
            product = selected_product["_source"]
            carousel_element = {
                TITLE: product[PRODUCT_NAME],
                SUBTITLE: f"Price: {product['price']}; Ratings: {product['ratings']}",
                IMAGE_URL: product["image"],
                BUTTONS: [
                    {
                        TITLE: PRODUCT_DETAILS,
                        PAYLOAD: f"{product['id']} details",
                        TYPE: POSTBACK,
                    },
                    {
                        TITLE: BUY_NOW,
                        PAYLOAD: PAYLOAD_BUTTON_BLOCKED,
                        TYPE: POSTBACK,
                    },
                    {
                        TITLE: ADD_TO_CART,
                        PAYLOAD: PAYLOAD_BUTTON_BLOCKED,
                        TYPE: POSTBACK,
                    },
                ],
            }
            carousel[PAYLOAD]["elements"].append(carousel_element)
        return carousel

    def __get_entities(self, tracker):
        is_show_more_triggered = tracker.get_slot(IS_SHOW_MORE_TRIGGERED)
        category = None
        sub_category = None
        color = None
        price_min = None
        price_max = None
        brand = None
        gender = None
        latest_message = None
        scroll_id = None
        show_more_count = 0
        if is_show_more_triggered:
            scroll_id = tracker.get_slot(SCROLL_ID)
            show_more_count = tracker.get_slot(SHOW_MORE_COUNT)
        else:
            category = next(tracker.get_latest_entity_values(CATEGORY), None)
            sub_category = next(tracker.get_latest_entity_values(SUB_CATEGORY), None)
            color = next(tracker.get_latest_entity_values(COLOR), None)
            price_min = next(tracker.get_latest_entity_values(MIN), None)
            price_max = next(tracker.get_latest_entity_values(MAX), None)
            brand = next(tracker.get_latest_entity_values(BRAND), None)
            gender = next(tracker.get_latest_entity_values(GENDER), None)
            latest_message = tracker.latest_message
        return (
            category,
            sub_category,
            color,
            price_min,
            price_max,
            brand,
            gender,
            show_more_count,
            latest_message,
            is_show_more_triggered,
            scroll_id,
        )

    def __get_returnable_slots(self, count, dispatcher, not_non_entities, scroll_id):
        slot_set = []
        if count > STOP_SHOW_MORE_COUNT:
            dispatcher.utter_message(template="utter_show_more_products")
            slot_set.append(
                SlotSet(ACTION_THAT_TRIGGERED_SHOW_MORE, ACTION_PRODUCT_INQUIRY)
            )
            slot_set.append(SlotSet(SCROLL_ID, scroll_id))
            logger.info(not_non_entities)
            for key, value in not_non_entities.items():
                slot_set.append(SlotSet(key, value))
        else:
            slot_set.append(SlotSet(ACTION_THAT_TRIGGERED_SHOW_MORE, None))
            slot_set.append(SlotSet(CATEGORY, None))
            slot_set.append(SlotSet(SUB_CATEGORY, None))
            slot_set.append(SlotSet(BRAND, None))
            slot_set.append(SlotSet(PRICE_MIN, None))
            slot_set.append(SlotSet(PRICE_MAX, None))
            slot_set.append(SlotSet(COLOR, None))
            slot_set.append(SlotSet(GENDER, None))
            slot_set.append(SlotSet(SCROLL_ID, None))
        return slot_set

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        slot_set = []
        count = MIN_ITEM_IN_CAROUSEL
        (
            category,
            sub_category,
            color,
            price_min,
            price_max,
            brand,
            gender,
            show_more_count,
            latest_message,
            is_show_more_triggered,
            scroll_id,
        ) = self.__get_entities(tracker)
        not_non_entities = self.__validate_entities(
            category,
            sub_category,
            color,
            gender,
            price_min,
            price_max,
            brand,
            scroll_id,
        )
        if not_non_entities != {}:
            products = self.__generate_query_to_elasticsearch(
                not_non_entities, latest_message
            )
            five_products, count, scroll_id = self.__get_five_products(
                products, is_show_more_triggered, show_more_count
            )
            carousel = self.__convert_response_to_carousel(five_products)
            dispatcher.utter_message(attachment=carousel)
            dispatcher.utter_message(template="utter_product_inquiry_info")
            slot_set = self.__get_returnable_slots(
                count, dispatcher, not_non_entities, scroll_id
            )
        else:
            dispatcher.utter_message(template="utter_product_inquiry_options")

        slot_set.append(SlotSet(SHOW_MORE_COUNT, count))
        slot_set.append(SlotSet(IS_SHOW_MORE_TRIGGERED, False))
        return slot_set


class ActionFeedbackReminder(Action):
    def name(self) -> Text:
        return "action_feedback_reminder"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        reminder_events = []
        timestamp = generic_utils.get_feedback_timestamp()
        feedback_event = events.ReminderScheduled(
            intent_name="EXTERNAL_feedback",
            trigger_date_time=timestamp,
            name="feedback_reminder",
            kill_on_user_message=True,
        )
        reminder_events.append(feedback_event)
        return reminder_events


class ActionStartFeedbackForm(Action):
    def name(self) -> Text:
        return "action_start_feedback_form"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        return_elements = []
        return_elements.append(events.ReminderCancelled(name="feedback_reminder"))
        return_elements.append(ActiveLoop("feedback_form"))
        return_elements.append(FollowupAction("feedback_form"))
        return return_elements


class ActionFeedbacksubmit(Action):
    def name(self) -> Text:
        return "action_feedback_submit"

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        dispatcher.utter_message(response="utter_feedback_submitted")
        return [SlotSet("feedback", None)]


class ActionProductDetails(Action):
    def name(self) -> Text:
        return "action_product_details"

    def __make_utter_message(self, product, dispatcher):
        if product["hits"]["total"]["value"] > 0:
            product = product["hits"]["hits"][0]["_source"]
            price_utter = (
                f"Brand:{product['brand']} \nPrice: {product['price']}"
                f"\nColor: {product['color']}\nRatings: {product['ratings']} "
                f"- by {product['ratings_count']}"
                f"\n[click here](https://sites.google.com/view/productdetailneuralspace/home) for more info"
            )
            dispatcher.utter_message(text=product["product_name"])
            dispatcher.utter_message(image=product["image"])

            dispatcher.utter_message(text=price_utter)
            dispatcher.utter_message(text=product["product_description"])
        else:
            dispatcher.utter_message(response="utter_wrong_product_id")

    def run(
        self,
        dispatcher,
        tracker: Tracker,
        domain: "DomainDict",  # noqa: F821
    ) -> List[Dict[Text, Any]]:
        product_id = tracker.get_slot("es_product_id")
        logger.info(product_id)
        if product_id is not None:
            query_builder = EsQueryBuilder()
            product = query_builder.product_search_with_id(product_id)
            self.__make_utter_message(product, dispatcher)
        else:
            dispatcher.utter_message(response="utter_invalid_product_id")
        return []
