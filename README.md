## Set Up
To set up the project, follow the steps;
```
sudo apt-get install postgresql postgresql-contrib \ postgis \ git
```
## On a Virtual Environment

```
Sudo apt-get install python-virtualenv
virtualenv venv
cd venv && . bin/activate
```
## Clone the system
```
git clone https://github.com/gltn/stdm-web.git
```
## Setting up DB
```
sudo -u postgres createuser -P USER_NAME_HERE
sudo -u postgres createdb -O USER_NAME_HERE DATABASE_NAME_HERE #Remember to change in settings.py
#Enable PostGIS
sudo -u postgres psql -c "CREATE EXTENSION postgis; CREATE EXTENSION postgis_topology;" DATABASE_NAME_HERE
```
## Installing Requirements
```
pip install -r requirements.txt
```
## Sync and Running application
```
cd stdmweb
python manage.py migrate
python manage.py runserver
on browser: localhost:8000
```
