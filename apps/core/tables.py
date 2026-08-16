"""Shared django-tables2 base class used by every list page's table.

Centralizes the two things every table needs: a `request` kwarg so
`render_*` methods can check permissions, and a helper for rendering the
Edit/Delete action buttons consistently. Delete is wired up client-side
by the existing shared modal (static/js/main.js) - only the button markup
lives here.
"""
import django_tables2 as tables
from django.utils.html import format_html


class BaseTable(tables.Table):
    def __init__(self, *args, request=None, **kwargs):
        self.request = request
        super().__init__(*args, **kwargs)

    def user_has_perm(self, perm):
        return bool(self.request and self.request.user.has_perm(perm))

    @staticmethod
    def action_buttons(edit_url=None, delete_url=None, item_name=""):
        edit_html = (
            format_html(
                '<a href="{}" class="btn btn-sm btn-outline-primary" hx-boost="false">'
                '<i class="bi bi-pencil"></i></a> ',
                edit_url,
            )
            if edit_url
            else ""
        )
        delete_html = (
            format_html(
                '<button type="button" class="btn btn-sm btn-outline-danger" '
                'data-delete-url="{}" data-item-name="{}"><i class="bi bi-trash"></i></button>',
                delete_url,
                item_name,
            )
            if delete_url
            else ""
        )
        return format_html('<div class="text-end text-nowrap">{}{}</div>', edit_html, delete_html)
