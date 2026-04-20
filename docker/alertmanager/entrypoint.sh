#!/bin/sh
# =============================================================================
# Kaasb Alertmanager entrypoint — renders env vars into alertmanager.yml
# =============================================================================
# Alertmanager doesn't expand ${VAR} placeholders in its config file, so we
# template the config at container start by substituting known env vars.
# The source template is mounted read-only at /etc/alertmanager/alertmanager.yml.tpl;
# the rendered result is written to /tmp/alertmanager.yml.
# =============================================================================
set -eu

SRC=/etc/alertmanager/alertmanager.yml.tpl
DST=/tmp/alertmanager.yml

cp "$SRC" "$DST"

for var in \
    ALERTMANAGER_DISCORD_WEBHOOK_URL \
    ALERTMANAGER_SMTP_FROM \
    ALERTMANAGER_SMTP_TO \
    ALERTMANAGER_SMTP_AUTH_USERNAME \
    ALERTMANAGER_SMTP_AUTH_PASSWORD \
; do
    eval "val=\${$var:-}"
    # Escape sed special characters in the replacement value
    esc=$(printf '%s' "$val" | sed -e 's/[\/&|]/\\&/g')
    sed -i "s|\${$var}|$esc|g" "$DST"
done

exec /bin/alertmanager \
    --config.file="$DST" \
    --storage.path=/alertmanager \
    --web.listen-address=:9093
