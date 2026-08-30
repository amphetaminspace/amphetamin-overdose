# Deploy amphetamin_Overdose on Phusion Passenger

## Prerequisites
- Server with Phusion Passenger installed (Apache or Nginx module)
- Python 3.11+
- PostgreSQL 14+
- Redis 7+

## Server Setup Steps

### 1. Install Dependencies

```bash
# Install Python 3.11+
sudo apt update
sudo apt install python3.11 python3.11-venv python3.11-dev

# Install PostgreSQL & Redis
sudo apt install postgresql postgresql-contrib redis-server

# Install TA-Lib (required for indicators)
wget http://prdownloads.sourceforge.net/ta-lib/ta-lib-0.4.0-src.tar.gz
tar -xzf ta-lib-0.4.0-src.tar.gz
cd ta-lib
./configure --prefix=/usr
make
sudo make install
cd .. && rm -rf ta-lib*
```

### 2. Create Database

```bash
sudo -u postgres psql -c "CREATE USER trader WITH PASSWORD 'trader';"
sudo -u postgres psql -c "CREATE DATABASE amphetamin_overdose OWNER trader;"
sudo -u postgres psql -c "GRANT ALL PRIVILEGES ON DATABASE amphetamin_overdose TO trader;"
```

### 3. Deploy Application

```bash
# Clone/copy app to server
cd /var/www
git clone <your-repo> amphetamin-overdose
cd amphetamin-overdose

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install --upgrade pip
pip install -r requirements.txt

# Create logs and models directories
mkdir -p logs models

# Set permissions
chmod 755 logs models
```

### 4. Configure Environment

```bash
# Create .env file
cp .env.example .env
nano .env

# Required settings:
# DATABASE_URL=postgresql://trader:trader@localhost:5432/amphetamin_overdose
# REDIS_URL=redis://localhost:6379/0
# BINANCE_API_KEY=your_key
# BINANCE_API_SECRET=your_secret
# BINANCE_TESTNET=true
# PAPER_TRADING=true
```

### 5. Passenger Configuration

#### Option A: Apache VirtualHost
```apache
<VirtualHost *:80>
    ServerName your-domain.com
    
    DocumentRoot /var/www/amphetamin-overdose/public
    
    PassengerAppRoot /var/www/amphetamin-overdose
    PassengerPython /var/www/amphetamin-overdose/venv/bin/python
    PassengerAppType wsgi
    PassengerStartupFile passenger_wsgi.py
    
    <Directory /var/www/amphetamin-overdose/public>
        Allow from all
        Options -MultiViews
    </Directory>
</VirtualHost>
```

#### Option B: Nginx Configuration
```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    root /var/www/amphetamin-overdose/public;
    
    passenger_enabled on;
    passenger_app_root /var/www/amphetamin-overdose;
    passenger_python /var/www/amphetamin-overdose/venv/bin/python;
    passenger_app_type wsgi;
    passenger_startup_file passenger_wsgi.py;
}
```

### 6. Restart Passenger

```bash
# Touch the restart file
touch /var/www/amphetamin-overdose/tmp/restart.txt

# Or restart the web server
sudo systemctl restart apache2
# or
sudo systemctl restart nginx
```

### 7. Verify Deployment

```bash
# Check Passenger status
sudo passenger-status

# Check application logs
tail -f /var/www/amphetamin-overdose/logs/amphetamin_*.log

# Test health endpoint
curl http://your-domain.com/health
```

## File Structure for Passenger

```
/var/www/amphetamin-overdose/
├── passenger_wsgi.py      # Passenger entry point
├── passenger.config.json  # Passenger config
├── web/
│   ├── dashboard.py       # Flask app
│   ├── templates/
│   └── static/
├── core/
├── strategies/
├── indicators/
├── ai/
├── risk/
├── portfolio/
├── learning/
├── optimization/
├── exchanges/
├── data/
├── config/
├── requirements.txt
├── .env
├── logs/
└── models/
```

## Troubleshooting

### Passenger shows "App not found"
- Check `passenger_wsgi.py` exists in app root
- Verify Python path is correct in config

### Import errors
- Ensure virtual environment is activated
- Check all packages installed: `pip install -r requirements.txt`

### Database connection failed
- Verify PostgreSQL is running: `sudo systemctl status postgresql`
- Check DATABASE_URL in .env

### Trading engine not starting
- Check logs: `tail -f logs/amphetamin_*.log`
- Ensure PAPER_TRADING=true for initial testing
- Verify API keys are valid

## Security Notes

1. **Never expose the dashboard publicly without authentication**
2. **Use HTTPS** with a reverse proxy or PassengerSSL
3. **Restrict access** to `/api/start`, `/api/stop` endpoints
4. **Keep API keys secure** in `.env` file (not in version control)
5. **Use a firewall** to limit access to the server

## Recommended: Add Basic Auth

To protect the dashboard, add to `passenger_wsgi.py`:

```python
from flask_httpauth import HTTPBasicAuth
from werkzeug.security import generate_password_hash, check_password_hash

auth = HTTPBasicAuth()
users = {
    "admin": generate_password_hash("your-secure-password")
}

@auth.verify_password
def verify_password(username, password):
    if username in users and check_password_hash(users.get(username), password):
        return username
```

Then protect routes with `@auth.login_required`.
