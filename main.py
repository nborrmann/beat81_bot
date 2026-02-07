# /// script
# dependencies = [
#   "requests",
# ]
# ///

import requests
from datetime import datetime
import os
import time

token = os.getenv("BEAT81_TOKEN")
user_id = os.getenv("BEAT81_USERID")
BOOKING_URL = "https://api.production.b81.io/api/tickets"

headers = {
    "authorization": f"Bearer {token}",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
}


def book(event_id):
    r = requests.post(
        BOOKING_URL,
        json={"user_id": user_id, "event_id": event_id},
        headers=headers,
    )
    r.raise_for_status()
    return r.json()


def load_bookings():
    response = requests.get(
        BOOKING_URL,
        params={
            "user_id": user_id,
            "$sort[event_date_begin]": 1,
            "event_date_begin_gte": datetime.now().astimezone().isoformat(timespec="milliseconds"),
            "status_ne": "cancelled",
            "$limit": 100,
            "$skip": 0,
        },
        headers=headers,
    )

    response.raise_for_status()
    return response.json()["data"]


def book_from_waitlist():
    bookings = load_bookings()

    booked_count = sum(
        booking["current_status"]["status_name"] == "booked" for booking in bookings
    )
    waitlist_count = sum(
        booking["current_status"]["status_name"] == "waitlisted" for booking in bookings
    )
    booked_dates = {
        datetime.fromisoformat(b["event"]["date_begin"].replace("Z", "+00:00")).date()
        for b in bookings
        if b["current_status"]["status_name"] == "booked"
    }
    print(
        datetime.now().isoformat(),
        f"Checking {len(bookings)} bookings ({booked_count} booked, {waitlist_count} waitlisted) ...",
    )

    success = False
    for booking in bookings:
        booking_date = datetime.fromisoformat(
            booking["event"]["date_begin"].replace("Z", "+00:00")
        ).date()
        is_waitlist = booking["current_status"]["status_name"] == "waitlisted"
        is_bookable = (
            booking["event"]["current_participants_count"]
            < booking["event"]["max_participants"]
        )

        if is_waitlist and is_bookable and booking_date not in booked_dates:
            print(
                booking["event"]["date_begin"],
                booking["event"]["location"]["name"],
                booking["current_status"]["status_name"],
                booking["event"]["current_participants_count"],
                booking["event"]["max_participants"],
            )

            print(book(booking["event"]["id"]))
            success = True

    return success


if __name__ == "__main__":
    if not book_from_waitlist():
        exit(1)
