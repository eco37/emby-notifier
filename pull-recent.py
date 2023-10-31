#!/usr/bin/python3 
# Dependencies: python3-requests
# FIXME: Handle cleanup of old entrys in database

import requests
import sqlite3
import os.path
import json
import configparser


config_file = 'config.ini'
basepath = os.path.dirname(os.path.abspath(__file__))

# Make sure the config file exists
if not os.path.exists(f'{basepath}/{config_file}'):
    print("Error: Cant find config!")
    exit(1)


config = configparser.ConfigParser()
config.read(f'{basepath}/{config_file}')


# Initializing the database if not already done
def check_database(conn):
    cursor = conn.cursor()

    # Create tables
    cursor.execute("CREATE TABLE IF NOT EXISTS shows (_id INTEGER PRIMARY KEY, id INTEGER NOT NULL, name TEXT NOT NULL, series_name TEXT NOT NULL, season_name TEXT NOT NULL, type TEXT NOT NULL, series_id INTEGER NOT NULL, season_id INTEGER NOT NULL, server_id TEXT NOT NULL, user_id TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(id,user_Id));");
    cursor.execute("CREATE TABLE IF NOT EXISTS movies (_id INTEGER PRIMARY KEY, id NUMBER NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, server_id TEXT NOT NULL, user_id TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(id,user_Id));");
 
    # Add triggers
    cursor.execute("CREATE TRIGGER IF NOT EXISTS clean_shows AFTER INSERT ON shows BEGIN DELETE FROM shows WHERE _id IN (SELECT _id FROM shows ORDER BY _id DESC LIMIT 10000, -1); END;");
    cursor.execute("CREATE TRIGGER IF NOT EXISTS clean_movies AFTER INSERT ON shows BEGIN DELETE FROM movies WHERE _id IN (SELECT _id FROM movies ORDER BY _id DESC LIMIT 10000, -1); END;");

    conn.commit()

# Get method for the recent API
def get_json(item_type, user):
    url = f'{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/emby/Users/{user}/Items/Latest?Limit={config["api"]["recent_pull_limit"]}&IncludeItemTypes={item_type}&GroupItems=false&EnableImages=false&EnableUserData=false&api_key={config["api"]["key"]}'
    
    try:
        r = requests.get(url)
        return r.json()
    except:
        return json.loads('{}')


def get_recent_shows(conn):
    cursor = conn.cursor()
    
    for user_id in json.loads(config["api"]["user_ids"]):
        data = get_json('Episode', user_id)
        
        for item in data:
            ret = cursor.execute("INSERT OR IGNORE INTO shows(id,name,series_name,season_name,type,series_id,season_id,server_id, user_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item['Id'], item['Name'], item['SeriesName'], item['SeasonName'], 
                item['Type'], item['SeriesId'], item['SeasonId'], item['ServerId'], user_id));
            
    conn.commit()
    

def get_recent_movies(conn):
    cursor = conn.cursor()
    
    for user_id in json.loads(config["api"]["user_ids"]):
        data = get_json('Movie', user_id)
        
        for item in data:
            ret = cursor.execute("INSERT OR IGNORE INTO movies(id,name,type,server_id, user_id) VALUES(?, ?, ?, ?, ?)",
                (item['Id'], item['Name'], item['Type'], item['ServerId'], user_id));
            
    conn.commit()


########################################################



sql_conn = sqlite3.connect(f'{basepath}/{config["files"]["database"]}')
check_database(sql_conn)

get_recent_shows(sql_conn)
get_recent_movies(sql_conn)

sql_conn.commit()
sql_conn.close()





