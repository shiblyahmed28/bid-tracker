#!/bin/sh
# Runs once a day for the life of the container (see the loop at the
# bottom). Connects to the `web` service over the internal Docker network —
# exactly the certificate a real browser would see — and warns if it's
# close to expiry. Let's Encrypt's shortlived profile issues certs valid
# for only ~160 hours, so Caddy renews far more often than a normal
# certificate; this is a monitor of last resort in case that ever fails
# silently. Output goes to this container's own log
# (`docker compose -f docker-compose.prod.yml logs certwatch`) — see
# docs/DEPLOY.md "Verifying certificate renewal".

WARN_THRESHOLD_HOURS=48

check_once() {
    if [ "${TLS_ENABLED}" != "1" ]; then
        echo "$(date -u +%FT%TZ) INFO certwatch: TLS_ENABLED is not 1 — nothing to check yet (HTTP verification mode)"
        return
    fi

    if [ -z "${SITE_ADDRESS}" ]; then
        echo "$(date -u +%FT%TZ) ERROR certwatch: SITE_ADDRESS is not set — cannot check the certificate"
        return
    fi

    enddate=$(echo | openssl s_client -connect "web:8080" -servername "${SITE_ADDRESS}" 2>/dev/null \
        | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)

    if [ -z "${enddate}" ]; then
        echo "$(date -u +%FT%TZ) ERROR certwatch: could not read a certificate from web:8080 — is Caddy up and has it obtained one yet?"
        return
    fi

    end_epoch=$(date -d "${enddate}" +%s 2>/dev/null)
    now_epoch=$(date -u +%s)

    if [ -z "${end_epoch}" ]; then
        echo "$(date -u +%FT%TZ) ERROR certwatch: could not parse certificate expiry '${enddate}'"
        return
    fi

    hours_left=$(( (end_epoch - now_epoch) / 3600 ))

    if [ "${hours_left}" -lt 0 ]; then
        echo "$(date -u +%FT%TZ) ERROR certwatch: certificate for ${SITE_ADDRESS} EXPIRED at ${enddate}"
    elif [ "${hours_left}" -lt "${WARN_THRESHOLD_HOURS}" ]; then
        echo "$(date -u +%FT%TZ) WARNING certwatch: certificate for ${SITE_ADDRESS} expires in ${hours_left}h (${enddate}) — renewal may have failed"
    else
        echo "$(date -u +%FT%TZ) INFO certwatch: certificate for ${SITE_ADDRESS} OK, expires in ${hours_left}h (${enddate})"
    fi
}

while true; do
    check_once
    sleep 86400
done
