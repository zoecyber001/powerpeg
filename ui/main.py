"""The PegPower platform shell (PegPower Core and its installable modules).

The bare "/" opens the person's last business, or their first. Every real page
sits under the /b/[business_id] shell, so it renders inside the Scaffold and
the platform tables are read for that business.

Module gating is two-sided: the rail only offers modules this business has
enabled, and every module route re-checks the same table, so a typed URL to a
disabled module answers with one honest sentence. The function re-gates every
action it serves; this UI is convenience, not the boundary.
"""
from workpeg.ui import (
    App, Router, Route, Shell, State, Store, Padding, Button, Authenticated,
    cookie, reload, navigate, workpeg,
)

from app_shell import AppShell
from components import EmptyState, ErrorState, LoadingState
from pages.not_found import NotFoundPage
from pages.overview import OverviewPage
from pages.front_desk import FrontDeskPage
from pages.module_page import ModulePage
from pages.quickpass import QuickPassPage
from pages.bookings import BookingsPage
from pages.booking_detail import BookingDetailPage
from pages.roompower import RoomPowerPage
from pages.roompower_device import RoomPowerDevicePage
from pages.commerce import MarketplacePage, HotelDetailPage, BusinessReservationsPage


class Landing(App):
    """The bare "/": open the person's last business, or their first."""

    no_business = State(False)
    error = State("")

    async def on_mount(self):
        cached = cookie.get("cachedBusiness")
        if cached:
            navigate("/b/" + cached)
            return
        try:
            biz = await workpeg.first_business()
            if biz:
                navigate("/b/" + biz)
                return
            self.no_business = True
        except Exception as e:
            self.error = str(e)

    def again(self):
        reload()

    def build(self):
        return Authenticated(self.body())

    def body(self):
        if self.error != "":
            return Padding(
                ErrorState(
                    self.error,
                    Button("Try again", variant="outline-gray", icon="refresh",
                           on_click=self.again),
                ),
                all=24,
            )
        if self.no_business:
            return Padding(
                EmptyState(
                    "building",
                    "You are not in a business yet",
                    "Ask an owner to add you, then check again.",
                    Button("Check again", variant="outline-gray",
                           icon="refresh", on_click=self.again),
                ),
                all=24,
            )
        return Padding(LoadingState("Opening your workspace..."), all=24)


class Main(Router):
    store = Store(business="", page_title="")
    routes = [
        Route("/", Landing),
        Route("/b/[business_id]", AppShell),
        Route("/b/[business_id]/", OverviewPage),
        Route("/b/[business_id]/front-desk", FrontDeskPage),
        Route("/b/[business_id]/bookings", BookingsPage),
        Route("/b/[business_id]/bookings/[booking_id]", BookingDetailPage),
        Route("/b/[business_id]/roompower", RoomPowerPage),
        Route("/b/[business_id]/roompower/[device_code]", RoomPowerDevicePage),
        Route("/b/[business_id]/m/[module_id]", ModulePage),
        Route("/b/[business_id]/quickpass", QuickPassPage),
        Route("/b/[business_id]/marketplace", MarketplacePage),
        Route("/b/[business_id]/marketplace/[stay_id]", HotelDetailPage),
        Route("/b/[business_id]/ecommerce/reservations", BusinessReservationsPage),
    ]
    not_found = NotFoundPage
