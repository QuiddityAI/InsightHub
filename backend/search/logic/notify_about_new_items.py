import logging
import os
import smtplib
from email.mime.text import MIMEText
from typing import Iterable

from columns.schemas import CellData, Criterion
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
    email_addresses: list[str] = collection.notification_emails.split(",")
    if not email_addresses:
        return
    language: str = "en"
    if collection.most_recent_search_task:
        language = collection.most_recent_search_task.settings.get("result_language", "en")
    text = notification_email[language]
    text = text.replace("{{ collection_name }}", collection.name)

    dataset: Dataset = Dataset.objects.select_related("schema").get(id=dataset_id)

    domain = "https://feldberg.absclust.com"
    if dataset.organization.domains:
        domain = "https://" + dataset.organization.domains[0]
    collection_url = f"{domain}/?organization_id={dataset.organization.id}&collection_id={collection.id}"  # type: ignore
    text = text.replace("{{ collection_url }}", collection_url)

    if not dataset.schema.default_search_fields:
        logging.warning("No default search fields set for dataset %s", dataset_id)
        return
    title_field = dataset.schema.default_search_fields[0]
    columns: list[CollectionColumn] = list(collection.columns.all())  # type: ignore
    new_item_texts: list[str] = []
    for item in new_collection_items:
        if not item.relevance >= ItemRelevance.APPROVED_BY_AI:
            continue
        metadata = item.metadata
        if not metadata:
            logging.warning("No metadata found for item %s", item.id)  # type: ignore
            continue
        item_text = f"{title_field}: {metadata.get(title_field, '-')}\n"
        for column in columns:
            data: CellData = CellData(**item.column_data.get(column.identifier, {}))
            if not data.value:
                continue
            if column.module == "relevance":
                assert isinstance(data.value, dict)
                criteria = [Criterion(**c) for c in data.value["criteria_review"]]
                for criterion in criteria:
                    item_text += "- " + str(criterion) + "\n"
            else:
                item_text += f"{column.name}: {data.value if data else '-'}\n"
        item_url = f"{collection_url}&item_details={item.dataset_id},{item.item_id}"  # type: ignore
        item_text += f"URL: {item_url}\n"
        item_text += "\n"
        new_item_texts.append(item_text)

    text = text.replace("{{ new_items }}", "\n\n".join(new_item_texts))

    for email_address in email_addresses:
        send_email("New items added in Quiddity", text, [email_address.strip()])


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
    if not password:
        logging.warning("Would have sent email but no password set")
        logging.warning(text)
        return
    assert host and port and user and password
    with smtplib.SMTP_SSL(host, port) as smtp_server:
        smtp_server.login(user, password)
        smtp_server.sendmail(sender, recipients, msg.as_string())
