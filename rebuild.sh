#!/bin/bash

podman-compose down -v
podman-compose up --build -d
podman-compose exec web python manage.py seed_demo
