from django.db import migrations


def migrate_policy_detail_structure(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for policy in Policy.objects.all():
        eligibility_text = (
            policy.eligibility.strip()
            if policy.eligibility
            else ""
        )

        if eligibility_text:
            eligibility_items = [eligibility_text]
        else:
            eligibility_items = []

        documents_text = (
            policy.required_documents.strip()
            if policy.required_documents
            else ""
        )

        if documents_text:
            required_document_items = [
                {
                    "label": item.strip(),
                    "issueMethod": None,
                    "linkUrl": None,
                }
                for item in documents_text.split(",")
                if item.strip()
            ]
        else:
            required_document_items = []

        policy.eligibility_items = eligibility_items
        policy.required_document_items = required_document_items

        policy.save(update_fields=["eligibility_items", "required_document_items"])


def reverse_policy_detail_structure(apps, schema_editor):
    Policy = apps.get_model("home", "Policy")

    for policy in Policy.objects.all():
        policy.eligibility = ", ".join(policy.eligibility_items or [])

        policy.required_documents = ", ".join(
            item.get("label", "")
            for item in (policy.required_document_items or [])
            if item.get("label")
        )

        policy.save(update_fields=["eligibility", "required_documents"])


class Migration(migrations.Migration):

    dependencies = [("home", "0007_policy_eligibility_items_and_more"),]

    operations = [
        migrations.RunPython(migrate_policy_detail_structure, reverse_policy_detail_structure),
    ]