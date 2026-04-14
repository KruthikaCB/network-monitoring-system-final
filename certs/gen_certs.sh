#!/bin/bash
# Generate self-signed SSL certificates for the TCP control channel
# Run this once before starting the server.

set -e
CERT_DIR="$(cd "$(dirname "$0")" && pwd)"

echo "[*] Generating CA key and certificate..."
openssl genrsa -out "$CERT_DIR/ca.key" 4096
openssl req -new -x509 -days 3650 -key "$CERT_DIR/ca.key" \
    -out "$CERT_DIR/ca.crt" \
    -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=NMS-CA/CN=NMS-RootCA"

echo "[*] Generating server key and CSR..."
openssl genrsa -out "$CERT_DIR/server.key" 4096
openssl req -new -key "$CERT_DIR/server.key" \
    -out "$CERT_DIR/server.csr" \
    -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=NMS/CN=localhost"

echo "[*] Signing server certificate with CA..."
openssl x509 -req -days 3650 \
    -in "$CERT_DIR/server.csr" \
    -CA "$CERT_DIR/ca.crt" \
    -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERT_DIR/server.crt"

echo "[*] Generating client key and CSR..."
openssl genrsa -out "$CERT_DIR/client.key" 4096
openssl req -new -key "$CERT_DIR/client.key" \
    -out "$CERT_DIR/client.csr" \
    -subj "/C=IN/ST=Karnataka/L=Bengaluru/O=NMS/CN=nms-client"

echo "[*] Signing client certificate with CA..."
openssl x509 -req -days 3650 \
    -in "$CERT_DIR/client.csr" \
    -CA "$CERT_DIR/ca.crt" \
    -CAkey "$CERT_DIR/ca.key" \
    -CAcreateserial \
    -out "$CERT_DIR/client.crt"

echo "[+] Certificates generated successfully:"
ls -la "$CERT_DIR"/*.crt "$CERT_DIR"/*.key
