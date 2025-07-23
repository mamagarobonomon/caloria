# ⚠️ DEPRECATED DOCUMENTATION

**These files are deprecated and should no longer be used. Please use `DEPLOYMENT_CONSOLIDATED.md` instead.**

---

## 🚫 **Deprecated Files**

| File | Issue | Replaced By |
|------|-------|------------|
| `DEPLOYMENT.md` | Uses old scripts, inconsistent service names | `DEPLOYMENT_CONSOLIDATED.md` |
| `SAFE_DEPLOYMENT_GUIDE.md` | Duplicate SSH setup, conflicting usernames | `DEPLOYMENT_CONSOLIDATED.md` |
| `SSH_CONFIG.md` | Duplicate SSH information | `DEPLOYMENT_CONSOLIDATED.md` Step 1 |
| `SSH_SETUP_GUIDE.md` | Duplicate SSH setup with different approach | `DEPLOYMENT_CONSOLIDATED.md` Step 1 |
| `vps_deploy_commands.txt` | Raw commands without context | `DEPLOYMENT_CONSOLIDATED.md` |
| `PRODUCTION_CONFIG.md` | Outdated credentials and placeholders | `DEPLOYMENT_CONSOLIDATED.md` Step 3 |

---

## ✅ **Use Instead**

**Single Source of Truth**: [`DEPLOYMENT_CONSOLIDATED.md`](./DEPLOYMENT_CONSOLIDATED.md)

This consolidated guide:
- ✅ Eliminates all duplications
- ✅ Uses consistent service names (`caloria-vip`)
- ✅ Has clear, step-by-step instructions
- ✅ Includes troubleshooting
- ✅ Is kept up-to-date

---

## 🗑️ **Files to Delete (Future Cleanup)**

These files contain duplicate/conflicting information:
- `DEPLOYMENT.md`
- `SSH_CONFIG.md` 
- `SSH_SETUP_GUIDE.md`
- `vps_deploy_commands.txt`
- `PRODUCTION_CONFIG.md`

**Keep**:
- `DEPLOYMENT_CONSOLIDATED.md` (main guide)
- `SAFE_DEPLOYMENT_GUIDE.md` (can be updated to reference consolidated guide)
- `GOOGLE_CLOUD_*.md` (separate feature documentation)

---

## 📅 **Migration Timeline**

- **✅ Created**: `DEPLOYMENT_CONSOLIDATED.md`
- **🔄 Update**: All scripts to reference new guide
- **📝 Next**: Update README.md to point to consolidated guide
- **🗑️ Future**: Remove deprecated files after validation 