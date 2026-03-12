#!/usr/bin/env bash
# chmod +x tests/scripts/verify-nixos.sh
#
# Verifies that nixos-infect.sh successfully converted a VM to NixOS.
# Usage: verify-nixos.sh <VM_IP> <SSH_KEY_PATH>
#
set -euo pipefail

VM_IP="${1:?Usage: verify-nixos.sh <VM_IP> <SSH_KEY_PATH>}"
SSH_KEY="${2:?Usage: verify-nixos.sh <VM_IP> <SSH_KEY_PATH>}"

SSH_OPTS="-o StrictHostKeyChecking=no -o ConnectTimeout=10 -o BatchMode=yes"
SSH="ssh $SSH_OPTS -i $SSH_KEY root@$VM_IP"

FAILURES=0

echo "==> Verifying NixOS installation on $VM_IP"

# 1. /etc/NIXOS marker exists
echo "--> Check: /etc/NIXOS marker"
if $SSH "test -f /etc/NIXOS"; then
  echo "    PASS: /etc/NIXOS exists"
else
  echo "    FAIL: /etc/NIXOS missing"
  FAILURES=$((FAILURES + 1))
fi

# 2. nixos-version command works
echo "--> Check: nixos-version"
if VERSION=$($SSH "nixos-version" 2>/dev/null); then
  echo "    PASS: NixOS version: $VERSION"
else
  echo "    FAIL: nixos-version not found or failed"
  FAILURES=$((FAILURES + 1))
fi

# 3. Failed systemd units (soft check, warning only)
echo "--> Check: systemd failed units (warning only)"
FAILED_UNITS=$($SSH "systemctl --failed --no-legend 2>/dev/null | wc -l" || echo "0")
if [ "$FAILED_UNITS" -gt 0 ]; then
  echo "    WARN: $FAILED_UNITS failed systemd unit(s):"
  $SSH "systemctl --failed 2>/dev/null" || true
else
  echo "    PASS: No failed systemd units"
fi

# 4. sshd is active
echo "--> Check: sshd active"
if $SSH "systemctl is-active sshd" >/dev/null 2>&1; then
  echo "    PASS: sshd is active"
else
  echo "    FAIL: sshd is not active"
  FAILURES=$((FAILURES + 1))
fi

# 5. Nix store integrity (fast check, no --check-contents)
echo "--> Check: nix-store verify"
if $SSH "nix-store --verify" >/dev/null 2>&1; then
  echo "    PASS: nix-store verified"
else
  echo "    FAIL: nix-store --verify failed"
  FAILURES=$((FAILURES + 1))
fi

# 6. Nix evaluator works
echo "--> Check: nix-instantiate eval"
if RESULT=$($SSH "nix-instantiate --eval -E '1 + 1'" 2>/dev/null); then
  if [ "$RESULT" = "2" ]; then
    echo "    PASS: nix-instantiate evaluates correctly"
  else
    echo "    FAIL: nix-instantiate returned '$RESULT', expected '2'"
    FAILURES=$((FAILURES + 1))
  fi
else
  echo "    FAIL: nix-instantiate failed"
  FAILURES=$((FAILURES + 1))
fi

echo ""
if [ "$FAILURES" -gt 0 ]; then
  echo "RESULT: FAILED ($FAILURES check(s) failed)"
  exit 1
fi

echo "RESULT: PASSED"
