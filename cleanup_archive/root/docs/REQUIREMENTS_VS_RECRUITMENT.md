# ⚠️ IMPORTANT: recruitment.docker.txt vs requirements.txt

**Issue:** Kesalahpahaman dimana `recruitment.docker.txt` dibaca sebagai file requirements untuk pip

---

## 🔴 The Problem

Docker build error:
```
ERROR: Invalid requirement: '╔════════════════════════════════════════════════════════════════════════════╗'
(from line 1 of requirements.txt)
```

**Why?** Ada confusion antara dua file:
1. **`recruitment.docker.txt`** ← Dokumentasi dengan decoration headers (BUKAN untuk pip)
2. **`requirements.txt`** ← File Python dependencies untuk pip (BENAR)

---

## 📋 File Purposes

### ✅ `requirements.txt` (Use this for Docker/pip)
```
amqp==5.3.1
asgiref==3.9.1
attrs==25.3.0
...
pywin32==311; sys_platform == 'win32'
...
```
- **Format:** Pure pip requirements (package==version)
- **Usage:** `pip install -r requirements.txt`
- **Docker:** `RUN pip install -r requirements.txt`
- **Line 1:** Starts with package name like `amqp==5.3.1`

### ❌ `recruitment.docker.txt` (DO NOT use for pip)
```
╔════════════════════════════════════════════════════════════════════════════╗
║                    DOCKER SETUP - ANTI-FAIL CHECKLIST                     ║
║                        (Comprehensive Verification)                       ║
╚════════════════════════════════════════════════════════════════════════════╝

## 1. Dockerfile Validation
...
```
- **Format:** Markdown documentation with box-drawing decoration
- **Usage:** Reference/checklist only
- **Docker:** NEVER use this for pip
- **Line 1:** Starts with decoration character `╔════`

---

## 🐳 Correct Dockerfile Configuration

### ✅ CORRECT (This is what we use)
```dockerfile
# Copy requirements
COPY requirements.txt .

# Create wheels
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt
```

### ❌ WRONG (Don't do this)
```dockerfile
# WRONG - This copies the decoration file!
COPY recruitment.docker.txt requirements.txt

# WRONG - This copies the wrong file!
COPY recruitment.docker.txt .
```

---

## 🔧 Why the Confusion?

1. `recruitment.docker.txt` was created as a **documentation/checklist** file
2. It has a similar name to requirements file, causing confusion
3. The `╔════` decoration in line 1 is NOT valid pip format
4. When Docker tries to `pip install -r` it fails because it's not valid requirements syntax

---

## ✅ Solution: Use requirements.txt ONLY

**In Dockerfile:**
```dockerfile
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt
```

**In docker-compose.yml or shell:**
```bash
# Correct
pip install -r requirements.txt
pip wheel -r requirements.txt

# Wrong
pip install -r recruitment.docker.txt  # ❌ Will fail with decoration error
```

---

## 📝 Files in Your Project

| File | Purpose | Use For | Format |
|------|---------|---------|--------|
| `requirements.txt` | Python dependencies | pip, docker | Package list |
| `recruitment.docker.txt` | Docker setup guide | Reference only | Markdown doc |
| `.env` | Environment config | Application config | Key=value |
| `docker-compose.yml` | Docker services | `docker-compose` | YAML |
| `Dockerfile` | Image build | `docker build` | Dockerfile syntax |

---

## 🎯 Remember

- ✅ **requirements.txt** = What pip needs
- ✅ **recruitment.docker.txt** = What you read for guidance
- ❌ **Never** use recruitment.docker.txt for pip or Docker builds

---

## 🚀 Quick Reference

```bash
# ✅ CORRECT - Always use requirements.txt
docker-compose build --no-cache

# ✅ CORRECT - Local testing
pip install -r requirements.txt

# ❌ WRONG - recruitment.docker.txt is for reading, not installing
pip install -r recruitment.docker.txt
```

---

**Status:** ✅ FIXED  
**Commit:** `194fe7ed` - "fix: Clarify Dockerfile to use requirements.txt, NOT recruitment.docker.txt"  
**Date:** 13 January 2025
