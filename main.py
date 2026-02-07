from datetime import datetime
import os
import time
import json
import base64
import json
from urllib import request, parse, error
from datetime import datetime

BOOKING_URL = "https://api.production.b81.io/api/tickets"
TOKEN = os.getenv("BEAT81_TOKEN")

# decode user_id from token
payload = TOKEN.split(".")[1]
data = json.loads(base64.urlsafe_b64decode(payload + "=" * (-len(payload) % 4)))
USER_ID = data["userId"]

headers = {
    "authorization": f"Bearer {TOKEN}",
    "user-agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/144.0.0.0 Safari/537.36",
    "content-type": "application/json",
}


def perform_request(req):
    try:
        with request.urlopen(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except error.HTTPError as e:
        body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {e.code}: {body}") from e


def book(event_id):
    payload = json.dumps({"user_id": USER_ID, "event_id": event_id}).encode("utf-8")
    return perform_request(
        request.Request(BOOKING_URL, data=payload, headers=headers, method="POST")
    )


def load_bookings():
    params = {
        "user_id": USER_ID,
        "$sort[event_date_begin]": 1,
        "event_date_begin_gte": datetime.now()
        .astimezone()
        .isoformat(timespec="milliseconds"),
        "status_ne": "cancelled",
        "$limit": 100,
        "$skip": 0,
    }

    url = f"{BOOKING_URL}?{parse.urlencode(params)}"
    return perform_request(request.Request(url, headers=headers, method="GET"))["data"]


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

            try:
                print(book(booking["event"]["id"]))
                booked_dates.add(datetime.fromisoformat(booking["event"]["date_begin"].replace("Z", "+00:00")).date())
            except Exception as e:
                print(e)
            success = True

    return success


if __name__ == "__main__":
    if not book_from_waitlist():
        exit(1)
