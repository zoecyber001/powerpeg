"""Shared UI building blocks for the PegPower Workpeg app.

These are the widgets the pages compose. They are intentionally thin: they
compose Workpeg primitives into the shapes the app uses repeatedly, and they
stay honest about loading, empty and error states.

The shape they share is a ruled register: a heading, hairline-separated rows,
and numbers set in the table's own type. That is what the product is — a
record of rooms, guests, codes, deals and requests — so the parts stay quiet
and let the rows carry the page.
"""
from workpeg.ui import (
    Component, Column, Container, Divider, Expanded, Icon, Row, Spacer,
    Spinner, Tag, Text,
)


class PageHeader(Component):
    """A page's title, one line under it, and a single supporting action."""

    def __init__(self, title, subtitle, action):
        self.title = title
        self.subtitle = subtitle
        self.action = action

    def build(self):
        return Row(
            Expanded(
                Column(
                    Text(self.title, variant="title"),
                    Text(self.subtitle, variant="muted"),
                    gap=4,
                ),
            ),
            self.action,
            align="center", gap=16,
        )


class LoadingState(Component):
    """While a page waits for its first answer: a line, not a hole."""

    def __init__(self, label):
        self.label = label

    def build(self):
        return Row(
            Spinner(size=16),
            Text(self.label, variant="muted"),
            gap=10, align="center",
        )


class EmptyState(Component):
    """Nothing here yet: what is missing, and the one way forward."""

    def __init__(self, icon, title, detail, action):
        self.icon = icon
        self.title = title
        self.detail = detail
        self.action = action

    def build(self):
        return Container(
            Column(
                Row(
                    Icon(self.icon, size=18, weight="thin"),
                    Text(self.title, weight="medium"),
                    gap=8, align="center",
                ),
                Text(self.detail, variant="muted"),
                Row(self.action, align="center"),
                gap=10, align="start",
            ),
            variant="card", padding=24,
        )


class ErrorState(Component):
    """A read failed: say what the platform said and offer a way on."""

    def __init__(self, message, action):
        self.message = message
        self.action = action

    def build(self):
        return Container(
            Column(
                Row(
                    Icon("alert-circle", size=18, weight="thin"),
                    Text("This page could not be read", weight="medium"),
                    gap=8, align="center",
                ),
                Text(self.message, variant="muted"),
                Row(self.action, align="center"),
                gap=10, align="start",
            ),
            variant="card", padding=24,
        )


class RecordTag(Component):
    """A stored status, toned by what it means rather than by its family.

    Only two readings matter: the record is live, or it is not. Anything the
    platform might store that needs attention is the one warm tone.
    """

    def __init__(self, status):
        self.status = status

    def build(self):
        if self.status == "":
            return Tag("Unset", tone="neutral", dot=True)
        elif (self.status == "active" or self.status == "available"
              or self.status == "confirmed" or self.status == "published"
              or self.status == "checked_in" or self.status == "approved"):
            return Tag(self.status, tone="success", dot=True)
        elif (self.status == "pending" or self.status == "awaiting"
              or self.status == "unpaid" or self.status == "hold"):
            return Tag(self.status, tone="warning", dot=True)
        else:
            return Tag(self.status, tone="neutral", dot=True)


class StatusTag(Component):
    """A guest's relationship to this business, as one word."""

    def __init__(self, status):
        self.status = status

    def build(self):
        if self.status == "active":
            return Tag("Active", tone="success", dot=True)
        elif self.status == "churned":
            return Tag("Churned", tone="neutral", dot=True)
        else:
            return Tag("Lead", tone="neutral", dot=True)


class StatCard(Component):
    """One real number, its label, and where it came from."""

    def __init__(self, label, value, detail):
        self.label = label
        self.value = value
        self.detail = detail

    def build(self):
        return Container(
            Column(
                Text(self.label, variant="caption"),
                Text(self.value, variant="title"),
                Text(self.detail, variant="muted"),
                gap=4, align="start",
            ),
            variant="card", padding=18,
        )


class MetricRow(Component):
    """One real number as a line in a register: label, source, figure."""

    def __init__(self, label, value, detail):
        self.label = label
        self.value = value
        self.detail = detail

    def build(self):
        return Column(
            Divider(),
            Row(
                Column(
                    Text(self.label),
                    Text(self.detail, variant="caption"),
                    gap=2,
                ),
                Spacer(),
                Text(self.value, variant="title"),
                gap=16, align="center",
            ),
            gap=10, align="stretch",
        )


class FactRow(Component):
    """One labelled fact in a register: the label, the rule, the value."""

    def __init__(self, label, value, ruled=True):
        self.label = label
        self.value = value
        self.ruled = ruled

    def build(self):
        if not self.ruled:
            return Row(
                Text(self.label, variant="muted"),
                Spacer(),
                Text(self.value, weight="medium"),
                gap=16, align="center",
            )
        return Column(
            Divider(),
            Row(
                Text(self.label, variant="muted"),
                Spacer(),
                Text(self.value, weight="medium"),
                gap=16, align="center",
            ),
            gap=8, align="stretch",
        )
