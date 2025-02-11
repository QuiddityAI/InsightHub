import logging
import os
import smtplib
from email.message import EmailMessage
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
    if not new_collection_items:
        return
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
    collection_url = f"{domain}/?organization_id={dataset.organization.id}&collection_id={collection.id}"
    text = text.replace("{{ collection_url }}", collection_url)

    if not dataset.schema.default_search_fields:
        logging.warning("No default search fields set for dataset %s", dataset_id)
        return
    title_field = dataset.schema.default_search_fields[0]
    columns: list[CollectionColumn] = list(collection.columns.all())
    new_item_texts: list[str] = []
    for item in new_collection_items:
        if not item.relevance >= ItemRelevance.APPROVED_BY_AI:
            continue
        metadata = item.metadata
        if not metadata:
            logging.warning("No metadata found for item %s", item.id)
            continue
        item_url = f"{collection_url}&item_details={item.dataset_id},{item.item_id}"
        item_text = f"### {metadata.get(title_field, 'New Item')} ([open]({item_url})):\n\n"
        for column in columns:
            data: CellData = CellData(**item.column_data.get(column.identifier, {}))
            if not data.value:
                continue
            if column.module == "relevance":
                assert isinstance(data.value, dict)
                criteria = [Criterion(**c) for c in data.value["criteria_review"]]
                for c in criteria:
                    item_text += f"- **{c.criteria}** {'✓' if c.fulfilled else '❌'}: {c.reason} (<i>'{c.supporting_quote}'</i>)\n"
            else:
                item_text += f"- **{column.name}**: {data.value if data else '-'}\n"
        item_text += "\n---\n"
        new_item_texts.append(item_text)

    if not new_item_texts:
        return

    text = text.replace("{{ new_items }}", "\n\n".join(new_item_texts))

    for email_address in email_addresses:
        send_markdown_email("New items added in Quiddity", text, [email_address.strip()])


def send_markdown_email(subject, markdown, recipients):
    import markdown as markdown_module

    html = markdown_module.markdown(markdown)
    send_email(subject, markdown, html, recipients)


def send_email(subject, plain_text, html, recipients):
    sender = os.getenv("NOTIFICATION_EMAIL_ADDRESS")
    if not sender:
        logging.warning("No email address set for sending notifications")
        return
    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = ", ".join(recipients)
    msg.set_content(plain_text)
    if html:
        msg.add_alternative(html, subtype="html")

    host = os.getenv("NOTIFICATION_EMAIL_SMTP_HOST")
    port = int(os.getenv("NOTIFICATION_EMAIL_SMTP_PORT", 0))
    user = os.getenv("NOTIFICATION_EMAIL_SMTP_USER")
    password = os.getenv("NOTIFICATION_EMAIL_SMTP_PASSWORD")
    if not password:
        logging.warning("Would have sent email but no password set")
        logging.warning(plain_text)
        return
    assert host and port and user and password
    with smtplib.SMTP_SSL(host, port) as smtp_server:
        smtp_server.login(user, password)
        smtp_server.sendmail(sender, recipients, msg.as_string())
