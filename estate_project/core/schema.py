GRAPH_SCHEMA = """
Database Schema

Estate
---------
estate_id
name

Resident
---------
resident_id
name
gender
phone
email
status
registered_at

Property
---------
property_id
property_number
property_type
bedrooms
bathrooms
status

Complaint
----------
complaint_id
title
description
category
priority
status

Manager
-------
manager_id
name
email
phone

MaintenanceTeam
---------------
team_id
team_name
specialization
phone
email

Relationships

(:Estate)-[:HAS_PROPERTY]->(:Property)

(:Resident)-[:LIVES_IN]->(:Property)

(:Resident)-[:RAISED]->(:Complaint)

(:Complaint)-[:ABOUT]->(:Property)

(:Complaint)-[:ASSIGNED_TO]->(:MaintenanceTeam)

(:Property)-[:MANAGED_BY]->(:Manager)
"""