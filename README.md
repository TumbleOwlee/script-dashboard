# Script Dashboard

This repository contains a simple script management dashboard created using [Flask]() and [Tailwindcss]().

## Quickstart

Just follow these steps to host the service:

1. Checkout the repository: `git clone https://github.com/TumbleOwlee/script-dashboard.git`
2. Generate certificate: `openssl req -x509 -newkey rsa:4096 -nodes -out certificate/cert.pem -keyout certificate/key.pem -days 365`
3. Start the service: `flask --app main --debug run -h 0.0.0.0 -p 5000 --cert certificate/cert.pem --key certificate/key.pem`

Exchange the values for host and port as required. Also if available and possible, use a non-self-signed certificate.

**DO NOT USE THE TEST CERTIFICATES OF THIS REPOSITORY!**

Additionally, you can run it as a `systemd` managed service using the provided service file template. Just exchange the working directory entry for a valid one and place it in `/etc/systemd/system/`.
