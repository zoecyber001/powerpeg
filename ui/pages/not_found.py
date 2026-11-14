"""An address this peg does not serve."""
from workpeg.ui import App, Padding, Center, Column, Text, Link, location


class NotFoundPage(App):
    def build(self):
        return Padding(
            Center(
                Column(
                    Text("Page not found", variant="heading"),
                    Text(f"{location.pathname} is not part of this app.",
                         variant="muted"),
                    Link("Back to the overview", href="/"),
                    gap=8, align="center",
                ),
            ),
            all=48,
        )
