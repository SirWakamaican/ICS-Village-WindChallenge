#!/bin/bash

# Directory to store generated certificates
CERT_DIR="mqtt-certs"
mkdir -p "$CERT_DIR"

# Subject Alternative Names for the server certificate
SERVER_ALT_NAMES="DNS:localhost,DNS:mqtt,IP:0.0.0.0"

# Temporary CA key (we'll remove it later)
TMP_CA_KEY="$CERT_DIR/tmp-ca.key"
CA_CERT="$CERT_DIR/ca.pem"     # final CA certificate

# Server files
SERVER_KEY="$CERT_DIR/server.key"
SERVER_CSR="$CERT_DIR/server.csr"
SERVER_CERT="$CERT_DIR/server.pem"

# Client files
CLIENT_KEY="$CERT_DIR/client.key"
CLIENT_CSR="$CERT_DIR/client.csr"
CLIENT_CERT="$CERT_DIR/client.pem"

# Expiry duration for certificates
DAYS_VALID=365

echo "====================================================================="
echo "1. Generate temporary CA key (will not persist) and CA certificate"
echo "====================================================================="
openssl genpkey -algorithm RSA -out "$TMP_CA_KEY" -pkeyopt rsa_keygen_bits:2048
openssl req -x509 -new -nodes -key "$TMP_CA_KEY" -sha256 -days "$DAYS_VALID" \
  -out "$CA_CERT" \
  -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=MQTT-CA"

echo "====================================================================="
echo "2. Generate server key"
echo "====================================================================="
openssl genpkey -algorithm RSA -out "$SERVER_KEY" -pkeyopt rsa_keygen_bits:2048

echo "====================================================================="
echo "3. Create temporary OpenSSL config for server SAN"
echo "====================================================================="
cat <<EOF > "$CERT_DIR/server.cnf"
[ req ]
default_bits        = 2048
prompt              = no
default_md          = sha256
req_extensions      = req_ext
distinguished_name  = req_dn

[ req_dn ]
C = US
ST = State
L = City
O = Organization
OU = OrgUnit
CN = localhost

[ req_ext ]
subjectAltName = $SERVER_ALT_NAMES
EOF

echo "====================================================================="
echo "4. Generate server CSR using server.cnf"
echo "====================================================================="
openssl req -new -key "$SERVER_KEY" \
  -out "$SERVER_CSR" \
  -config "$CERT_DIR/server.cnf"

echo "====================================================================="
echo "5. Sign server certificate with CA, embedding SAN"
echo "====================================================================="
openssl x509 -req -in "$SERVER_CSR" \
  -CA "$CA_CERT" -CAkey "$TMP_CA_KEY" -CAcreateserial \
  -out "$SERVER_CERT" -days "$DAYS_VALID" -sha256 \
  -extfile "$CERT_DIR/server.cnf" -extensions req_ext

echo "====================================================================="
echo "6. Generate client key"
echo "====================================================================="
openssl genpkey -algorithm RSA -out "$CLIENT_KEY" -pkeyopt rsa_keygen_bits:2048

echo "====================================================================="
echo "7. Generate client CSR and sign with CA"
echo "====================================================================="
openssl req -new -key "$CLIENT_KEY" -out "$CLIENT_CSR" \
  -subj "/C=US/ST=State/L=City/O=Organization/OU=OrgUnit/CN=mqtt-client"

openssl x509 -req -in "$CLIENT_CSR" \
  -CA "$CA_CERT" -CAkey "$TMP_CA_KEY" -CAcreateserial \
  -out "$CLIENT_CERT" -days "$DAYS_VALID" -sha256

echo "====================================================================="
echo "8. Clean up temporary files (including CA private key)"
echo "====================================================================="
rm -f "$TMP_CA_KEY"               \
      "$CERT_DIR/server.csr"      \
      "$CERT_DIR/server.cnf"      \
      "$CLIENT_CSR"               \
      "$CERT_DIR/ca-cert.srl"

echo "====================================================================="
echo "Generated final files in '$CERT_DIR':"
echo "  CA Certificate:       $CA_CERT"
echo "  Server Private Key:   $SERVER_KEY"
echo "  Server Certificate:   $SERVER_CERT"
echo "  Client Private Key:   $CLIENT_KEY"
echo "  Client Certificate:   $CLIENT_CERT"
echo "====================================================================="
