import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Iterable

from columns.schemas import CellData
from data_map_backend.models import (
    CollectionColumn,
    CollectionItem,
    DataCollection,
    Dataset,
)
from data_map_backend.schemas import ItemRelevance
from search.prompts import notification_email


def notify_about_new_items(
    dataset_id: int, collection: DataCollection, new_collection_items: Iterable[CollectionItem]
):
    email_addresses = collection.notification_emails.split(",")
    if not email_addresses:
        return
    language = "en"
    if collection.most_recent_search_task:
        language = collection.most_recent_search_task.settings.get("result_language", "en")
    text = notification_email[language]

    new_item_texts = []

    dataset = Dataset.objects.select_related("schema").get(id=dataset_id)
    fields: list | None = dataset.schema.descriptive_text_fields
    if not isinstance(fields, list):
        return
    assert isinstance(fields, list) and len(fields) > 0
    columns: list[CollectionColumn] = list(collection.columns.all())
    for item in new_collection_items:
        if not item.relevance >= ItemRelevance.APPROVED_BY_AI:
            continue
        item_text = ""
        for field in fields:
            item_text += f"{field}: {item.metadata.get(field, '-')}\n"
        for column in columns:
            data: CellData | None = item.column_data.get(column.identifier)
            item_text += f"{column.name}: {data.value if data else '-'}\n"
        new_item_texts.append(item_text)

    text = text.replace("{{ new_items }}", "\n\n".join(new_item_texts))

    for email_address in email_addresses:
        send_email("New items added in Quiddity", text, [email_address])


def send_email(subject, text, recipients):
    sender = os.getenv("NOTIFICATION_EMAIL_ADDRESS")
    if not sender:
        logging.warning("No email address set for sending notifications")
        return
    msg = MIMEText(text)
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    host = os.getenv("NOTIFICATION_EMAIL_SMTP_HOST")
    port = int(os.getenv("NOTIFICATION_EMAIL_SMTP_PORT", 0))
    user = os.getenv("NOTIFICATION_EMAIL_SMTP_USER")
    password = os.getenv("NOTIFICATION_EMAIL_SMTP_PASSWORD")
    assert host and port and user and password
    with smtplib.SMTP_SSL(host, port) as smtp_server:
        smtp_server.login(user, password)
        smtp_server.sendmail(sender, recipients, msg.as_string())
