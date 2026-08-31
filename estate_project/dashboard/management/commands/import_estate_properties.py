import csv
import os

from django.core.management.base import BaseCommand, CommandError

from core.neo4j_connection import Neo4jConnection


class Command(BaseCommand):
    help = "Import 50 Lagos estate properties into the existing Neo4j graph."

    def add_arguments(self, parser):
        parser.add_argument(
            "--file",
            default=os.path.join(
                os.path.expanduser("~"),
                "Downloads",
                "estate_properties_50.csv",
            ),
            help="Path to the estate properties CSV file.",
        )

    def handle(self, *args, **options):
        csv_path = options["file"]

        if not os.path.exists(csv_path):
            raise CommandError(
                f"CSV file not found: {csv_path}"
            )

        with open(
            csv_path,
            "r",
            encoding="utf-8-sig",
            newline=""
        ) as csv_file:
            reader = csv.DictReader(csv_file)
            rows = list(reader)

        if not rows:
            raise CommandError("CSV file is empty.")

        if len(rows) != 50:
            raise CommandError(
                f"Expected exactly 50 properties, but found {len(rows)}."
            )

        db = Neo4jConnection()

        imported = 0
        skipped = 0

        try:
            # Find the next available property number.
            existing_numbers = db.query(
                """
                MATCH (p:Property)
                RETURN p.property_number AS property_number
                """
            )

            used_numbers = []

            for record in existing_numbers:
                value = record.get("property_number")

                if isinstance(value, str) and value.startswith("P"):
                    try:
                        used_numbers.append(
                            int(value[1:])
                        )
                    except ValueError:
                        pass

            next_property_number = (
                max(used_numbers, default=0) + 1
            )

            for row in rows:
                estate_name = (row.get("Estate") or "").strip()
                title = (row.get("Title") or "").strip()
                property_type = (
                    row.get("Property_Type") or ""
                ).strip()
                bedrooms_raw = (
                    row.get("Bedrooms") or ""
                ).strip()

                if not estate_name:
                    self.stdout.write(
                        self.style.WARNING(
                            "Skipped row with no estate name."
                        )
                    )
                    skipped += 1
                    continue

                if not title:
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped row for {estate_name}: "
                            "missing title."
                        )
                    )
                    skipped += 1
                    continue

                # Convert bedrooms to an integer where possible.
                try:
                    bedrooms = int(float(bedrooms_raw))
                except (ValueError, TypeError):
                    bedrooms = 0

                # Reuse the estate if it already exists.
                estate_result = db.query(
                    """
                    MATCH (e:Estate)
                    WHERE toLower(e.name) = toLower($estate_name)
                    RETURN e.estate_id AS estate_id,
                           e.name AS name
                    LIMIT 1
                    """,
                    {
                        "estate_name": estate_name
                    }
                )

                if estate_result:
                    estate_id = estate_result[0]["estate_id"]
                    actual_estate_name = estate_result[0]["name"]
                else:
                    # Generate the next estate ID.
                    estate_ids = db.query(
                        """
                        MATCH (e:Estate)
                        RETURN e.estate_id AS estate_id
                        """
                    )

                    used_estate_numbers = []

                    for record in estate_ids:
                        value = record.get("estate_id")

                        if (
                            isinstance(value, str)
                            and value.startswith("E")
                        ):
                            try:
                                used_estate_numbers.append(
                                    int(value[1:])
                                )
                            except ValueError:
                                pass

                    next_estate_number = (
                        max(
                            used_estate_numbers,
                            default=0
                        ) + 1
                    )

                    estate_id = (
                        f"E{next_estate_number:03d}"
                    )

                    estate_create = db.query(
                        """
                        CREATE (e:Estate {
                            estate_id: $estate_id,
                            name: $estate_name,
                            state: "Lagos",
                            status: "Active"
                        })
                        RETURN e.estate_id AS estate_id,
                               e.name AS name
                        """,
                        {
                            "estate_id": estate_id,
                            "estate_name": estate_name,
                        }
                    )

                    actual_estate_name = (
                        estate_create[0]["name"]
                    )

                # Prevent duplicate imports if the command
                # is accidentally run again.
                duplicate = db.query(
                    """
                    MATCH (e:Estate)-[:HAS_PROPERTY]->(p:Property)
                    WHERE e.estate_id = $estate_id
                      AND p.property_number = $title
                    RETURN p.property_id AS property_id
                    LIMIT 1
                    """,
                    {
                        "estate_id": estate_id,
                        "title": title,
                    }
                )

                if duplicate:
                    skipped += 1
                    self.stdout.write(
                        self.style.WARNING(
                            f"Skipped duplicate: {title} "
                            f"→ {actual_estate_name}"
                        )
                    )
                    continue

                property_id = (
                    f"P{next_property_number:03d}"
                )

                property_number = (
                    f"DATA-{next_property_number:03d}"
                )

                result = db.query(
                    """
                    MATCH (e:Estate)
                    WHERE e.estate_id = $estate_id

                    CREATE (p:Property {
                        property_id: $property_id,
                        property_number: $property_number,
                        property_type: $property_type,
                        bedrooms: $bedrooms,
                        bathrooms: null,
                        status: "Available",
                        source_title: $title
                    })

                    CREATE (e)-[:HAS_PROPERTY]->(p)

                    RETURN p.property_id AS property_id,
                           e.name AS estate
                    """,
                    {
                        "estate_id": estate_id,
                        "property_id": property_id,
                        "property_number": property_number,
                        "property_type": property_type,
                        "bedrooms": bedrooms,
                        "title": title,
                    }
                )

                if result:
                    imported += 1
                    next_property_number += 1

                    self.stdout.write(
                        self.style.SUCCESS(
                            f"Imported {property_id} "
                            f"→ {actual_estate_name}"
                        )
                    )
                else:
                    skipped += 1

            self.stdout.write("")
            self.stdout.write(
                self.style.SUCCESS(
                    f"Import complete: {imported} properties "
                    f"imported, {skipped} skipped."
                )
            )

        finally:
            db.close()