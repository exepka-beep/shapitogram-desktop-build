#!/bin/bash
# Remove the `coder` SSH account, keeping a restore archive of everything it owned.
set -uo pipefail

U=coder
STAMP=$(date +%Y%m%d-%H%M%S)
BK=/root/backups/coder-user-$STAMP
mkdir -p "$BK"

echo "=== BEFORE"
id "$U" || { echo "no such user"; exit 0; }
ps -u "$U" -o pid=,cmd= 2>/dev/null | head -10

echo "=== BACKUP -> $BK"
tar czf "$BK/home.tar.gz" -C /home "$U" 2>/dev/null
getent passwd "$U" > "$BK/passwd.entry"
getent shadow "$U" > "$BK/shadow.entry"
getent group  "$U" > "$BK/group.entry"
getent group sudo | tr ',' '\n' | grep -x "$U" > "$BK/sudo-membership.txt" 2>/dev/null || true
ps -u "$U" -o pid=,ppid=,cmd= > "$BK/processes.txt" 2>/dev/null || true
ss -tnp 2>/dev/null | grep -i "uid:1001" > "$BK/sockets.txt" 2>/dev/null || true
ls -lh "$BK"

echo "=== KILL SESSIONS"
loginctl terminate-user "$U" 2>/dev/null || true
pkill -TERM -u "$U" 2>/dev/null || true
sleep 3
pkill -KILL -u "$U" 2>/dev/null || true
sleep 1
echo "   remaining procs: $(ps -u "$U" --no-headers 2>/dev/null | wc -l)"

echo "=== DELETE"
userdel -r "$U" 2>&1 | grep -v 'mail spool' || true

echo "=== AFTER"
id "$U" 2>&1 | head -1
echo "   home exists: $([ -d /home/$U ] && echo yes || echo no)"
echo "   sudo group: $(getent group sudo | cut -d: -f4)"
echo "   uid 1001 procs: $(ps -eo uid=,pid=,cmd= | awk '$1==1001' | wc -l)"
echo "   sessions: $(loginctl list-sessions --no-legend 2>/dev/null | awk '$3==1001' | wc -l)"
echo "   sshd listening: $(ss -ltn | grep -c ':4443')"
