# Google Cloud OAuth 2.0 Setup Guide for Fashion World Pro

Follow these step-by-step instructions to configure Google Cloud OAuth 2.0 authentication for Fashion World Pro.

---

## 1. Google Cloud Console Configuration

1. Go to the [Google Cloud Console](https://console.cloud.google.com/).
2. Select an existing project or create a new one (e.g., Fashion World Pro).
3. Navigate to **APIs & Services** > **OAuth consent screen**:
   - User Type: **External**
   - App name: **Fashion World Pro**
   - User support email: Select your email
   - Developer contact email: Enter your email
   - Scopes: Add or verify .../auth/userinfo.email, .../auth/userinfo.profile, and openid.
   - Save and continue.
4. Navigate to **APIs & Services** > **Credentials**:
   - Click **+ CREATE CREDENTIALS** > **OAuth client ID**.
   - Application type: **Web application**
   - Name: **Fashion World Pro Web Client**

---

## 2. Authorized Origins & Redirect URIs

In the OAuth Client ID settings under **Authorized JavaScript origins** and **Authorized redirect URIs**, enter the exact URIs below:

### AUTHORIZED JAVASCRIPT ORIGINS
```text
http://127.0.0.1:5000
http://localhost:5000
```

### AUTHORIZED REDIRECT URIS
```text
http://127.0.0.1:5000/auth/google/callback
http://localhost:5000/auth/google/callback
```

---

## 3. Configure Your .env File

Once created, Google will display your **Client ID** and **Client Secret**.

Open `c:\Users\kasul\Downloads\Fashion World pro\.env` and paste your credentials:

```env
# Google Cloud OAuth 2.0 Credentials
GOOGLE_CLIENT_ID=YOUR_CLIENT_ID_HERE.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=YOUR_CLIENT_SECRET_HERE

# Enable HTTP for local OAuth testing
OAUTHLIB_INSECURE_TRANSPORT=1
```

> **Security Note:** Never commit your .env file or share your GOOGLE_CLIENT_SECRET.

---

## 4. How Google Login Works in Fashion World Pro

1. **User clicks "Continue with Google"** on /login or /register.
2. Flask redirects to /auth/google.
3. Authlib generates the secure OAuth URL and sends the user to Google's consent screen.
4. After user authorization, Google redirects back to /auth/google/callback with an authorization code.
5. Flask exchanges the code for tokens and extracts user profile info (email, 
ame, sub).
6. Flask looks up or creates the local customer in instance/fashion_world.db.
7. login_user() authenticates the session and redirects to /dashboard.
