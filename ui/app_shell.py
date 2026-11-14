"""The PegPower platform chrome.

Scaffold draws sign-in, the rail, Search, Workpeg AI, the business switcher and
the top bar; this file only fills its slots.

The rail lists every module destination. The compiler only accepts a static
child list (no conditional or generated ``NavItem``\\ s), so the rail cannot
hide a row per business — the gating is done one level down instead: every
module route reads the business's ``business_modules`` table and, when the
module is not enabled, answers with one honest sentence rather than an empty
imitation of the page. The Overview page lists what is actually on, from the
same table. The function re-gates every action it serves, so none of this is
the security boundary.
"""
from workpeg.ui import Outlet, Shell, Text, biz_url, set_color_scheme, store
from workpeg.ui.scaffold import NavFixed, NavItem, NavSection, Scaffold


class AppShell(Shell):

    async def on_mount(self):
        # Follow the device's light or dark setting, live.
        set_color_scheme("system")

    def build(self):
        # The platform's Scaffold carries the session gate itself (and
        # exposes the signed-in user, whose row the role gate reads).
        return Scaffold(
            NavSection(
                "PegPower Core",
                NavItem("Overview", biz_url("/"), icon="layout-grid",
                        ),
            ),
            NavSection(
                "Modules",
                NavItem("Commerce", biz_url("/ecommerce/reservations"),
                        icon="credit-card"),
                NavItem("QuickPass", biz_url("/quickpass"), icon="id-badge"),
                NavItem("Guest Experience & Ops",
                        biz_url("/m/guesthub"),
                        icon="sparkles"),
                NavItem("RoomPower", biz_url("/roompower"),
                        icon="bolt"),
            ),
            NavSection(
                "Operations",
                NavItem("Front desk", biz_url("/front-desk"),
                        icon="building"),
                NavItem("Roles", biz_url("/roles"), icon="shield-lock"),
            ),
            NavSection(
                "Customer experience",
                NavItem("Marketplace", biz_url("/marketplace"),
                        icon="tag"),
                NavItem("My bookings", biz_url("/customer/bookings"),
                        icon="calendar"),
            ),
            fixed=NavFixed(NavItem("Home", biz_url("/"), icon="home")),
            top_nav=Text(store.page_title, weight="semibold"),
            main=Outlet(),
        )
