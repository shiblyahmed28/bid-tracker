FROM alpine:3

RUN apk add --no-cache openssl coreutils

COPY check-cert.sh /usr/local/bin/check-cert.sh
RUN chmod +x /usr/local/bin/check-cert.sh \
    && addgroup -g 1000 certwatch \
    && adduser -D -u 1000 -G certwatch certwatch

USER certwatch

ENTRYPOINT ["/usr/local/bin/check-cert.sh"]
