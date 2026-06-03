#!/usr/bin/env bash
set -e

mkdir -p /app/data

cd /app
mvn package -DskipTests -q

exec java -jar target/finledger.jar
