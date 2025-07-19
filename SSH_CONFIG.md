# SSH Connection Configuration

## 🔐 **CRITICAL REQUIREMENT: Always Use VPS User**

**⚠️ NEVER connect as root! Always use the 'vps' user for all server connections.**

## Connection Details

- **Server IP**: `162.248.225.106`
- **Username**: `vps` (NOT root!)
- **Port**: `22` (default)

## SSH Command

```bash
ssh vps@162.248.225.106
```

## Why VPS User?

1. **Security**: Root access should be limited
2. **Best Practice**: Using dedicated user accounts
3. **Sudo Access**: The 'vps' user has sudo privileges when needed
4. **Audit Trail**: Better logging and accountability

## For Deployments

When deploying or updating code, always connect as:

```bash
# Connect to server
ssh vps@162.248.225.106

# Update application
cd /var/www/caloria && sudo -u caloria bash -c 'git pull origin main && source venv/bin/activate && pip install -r requirements.txt' && sudo supervisorctl restart caloria-vip
```

## Quick Reference

- **Initial Setup**: `ssh vps@162.248.225.106`
- **Code Updates**: Use the update command above
- **Log Checking**: `sudo tail -f /var/log/supervisor/caloria-vip.log`
- **Service Status**: `sudo supervisorctl status caloria-vip`

**Remember: VPS user only! 🔑** 