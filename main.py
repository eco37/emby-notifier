#!/usr/bin/python3 
# Dependencies: python3-requests

import requests
import sqlite3
import argparse
import os.path
import json
import smtplib, ssl
import configparser
from email.utils import formataddr
from pathlib import Path
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

config_file = 'config.ini'

if not os.path.exists(config_file):
    print("Error: Cant find config!")

config = configparser.ConfigParser()
config.read(config_file)


def check_database(conn):
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS shows (_id INTEGER PRIMARY KEY, id INTEGER NOT NULL, name TEXT NOT NULL, series_name TEXT NOT NULL, season_name TEXT NOT NULL, type TEXT NOT NULL, series_id INTEGER NOT NULL, season_id INTEGER NOT NULL, server_id TEXT NOT NULL, user_id TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(id,user_Id));");
    cursor.execute("CREATE TABLE IF NOT EXISTS movies (_id INTEGER PRIMARY KEY, id NUMBER NOT NULL, name TEXT NOT NULL, type TEXT NOT NULL, server_id TEXT NOT NULL, user_id TEXT NOT NULL, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP, UNIQUE(id,user_Id));");
    
    conn.commit()


def get_json(item_type, user):
    url = f'{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/emby/Users/{user}/Items/Latest?Limit={config["api"]["recent_pull_limit"]}&IncludeItemTypes={item_type}&GroupItems=false&EnableImages=false&EnableUserData=false&api_key={config["api"]["key"]}'
    
    try:
        r = requests.get(url)
        print(url, r)
        #r.json()
        return r.json()
    except:
        print("ERROR")
        return json.loads('{}')


def get_recent_shows(conn):
    cursor = conn.cursor()
    print( config.get("api","user_ids") )
    for user_id in json.loads(config["api"]["user_ids"]):
        data = get_json('Episode', user_id)
        
        for item in data:
            print(item['Name'], item['SeriesName'])
            
            ret = cursor.execute("INSERT OR IGNORE INTO shows(id,name,series_name,season_name,type,series_id,season_id,server_id, user_id) VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (item['Id'], item['Name'], item['SeriesName'], item['SeasonName'], 
                item['Type'], item['SeriesId'], item['SeasonId'], item['ServerId'], user_id));
            
    conn.commit()
    

def get_recent_movies(conn):
    cursor = conn.cursor()
    for user_id in json.loads(config["api"]["user_ids"]):
        data = get_json('Movie', user_id)
        
        for item in data:
            print(item['Name'])
            
            ret = cursor.execute("INSERT OR IGNORE INTO movies(id,name,type,server_id, user_id) VALUES(?, ?, ?, ?, ?)",
                (item['Id'], item['Name'], item['Type'], item['ServerId'], user_id));
            
    conn.commit()


def send_mail(conn):
    cursor = conn.cursor()
    context = ssl.create_default_context()
    print(config["mail"]["smtp_host"], config["mail"]["smtp_port"])
    if config["mail"]["smtp_encryption_method"] == 'TLS':
        server = smtplib.SMTP(config["mail"]["smtp_host"], config["mail"]["smtp_port"])
        server.starttls(context=context) # Secure the connection with TLS
    elif config["mail"]["smtp_encryption_method"] == 'SSL':
        server = smtplib.SMTP_SSL(config["mail"]["smtp_host"], config["mail"]["smtp_port"], context=context)
    else:
        print("Error: Unknown encryption method!")
        return
        
    server.login(config["mail"]["smtp_user"], config["mail"]["smtp_password"])
    
    print(json.loads(config["api"]["user_ids"]))
    
    for user_id, email in json.loads(config["api"]["user_ids"]).items():
        print(user_id, email)
        shows_rows = cursor.execute(f'SELECT series_name, series_id, server_id FROM shows WHERE user_id = "{user_id}" and timestamp > DATETIME("now", "-{config["mail"]["recent_interval"]} seconds") GROUP BY series_id ORDER BY timestamp, _id ASC LIMIT {config["mail"]["recent_limit"]};').fetchall();
        movies_rows = cursor.execute(f'SELECT name, id, server_id FROM movies WHERE user_id = "{user_id}" and timestamp > DATETIME("now", "-{config["mail"]["recent_interval"]} seconds") ORDER BY timestamp, _id ASC LIMIT {config["mail"]["recent_limit"]};').fetchall();
        
        shows_plain = ''
        shows_html = ''
        movies_plain = ''
        movies_html = ''
        
        columns = int(config["mail"]["poster_colums"])
        for count, show in enumerate(shows_rows):
            print(show)
            shows_plain += f"- {show[0]}\n"
            shows_html += f'<td><a href="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/web/index.html#!/item?id={show[1]}&serverId={show[2]}"><img src="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/emby/Items/{show[1]}/Images/Primary?maxHeight=494&amp;maxWidth=329&amp;quality=90"></a></td>'
            columns -= 1
            if columns <= 0 and count != len(shows_rows)-1: 
                columns = int(config["mail"]["poster_colums"])
                shows_html += f"</tr><tr>\n"
                
        if columns != int(config["mail"]["poster_colums"]):
            for i in range(columns):
                shows_html += f"<td></td>\n"
        
        columns = int(config["mail"]["poster_colums"])
        for count, movie in enumerate(movies_rows):
            movies_plain += f"- {movie[0]}\n"
            movies_html += f'<td><a href="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/web/index.html#!/item?id={movie[1]}&serverId={movie[2]}"><img src="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/emby/Items/{movie[1]}/Images/Primary?maxHeight=494&amp;maxWidth=329&amp;quality=90"></a></td>\n'
            columns -= 1
            if columns <= 0 and count != len(shows_rows)-1: 
                columns = int(config["mail"]["poster_colums"])
                movies_html += f"</tr><tr>\n"
                
        if columns != int(config["mail"]["poster_colums"]):
            for i in range(columns):
                movies_html += f"<td></td>\n"
                
        print(shows_plain)
        print(shows_html)
        print(movies_plain)
        print(movies_html)
        
        print(len(shows_rows), len(movies_rows))
        if len(shows_rows) > 0 or len(movies_rows) > 0:
            msg = MIMEMultipart('alternative')
            msg['Subject'] = "Emby - Recently Added"
            msg['From'] = formataddr(('Emby Notification', config["mail"]["email_from"])) 
            msg['To'] = email
            print(msg['To'])
            # Plain-text version of content
            plain_text = f"Recently Added\n\n"
            if len(shows_plain) > 0:
                plain_text += f'TV-Shows\n{shows_plain}\n\n'
            
            if len(movies_plain) > 0:
                plain_text += f'Movies\n{movies_plain}\n'
            #1010 24
            # html version of content
            html_content = """\
                <html>
                <head>
                    <style>
                        body { width: 100%; }
                        div.wrapper { width: 460px; }
                        img { border-radius: 5%; }
                        th { font-size: 24px; }
                        td {vertical-align: middle; text-align: center;}
                        h1 { font-size: 30px; white-space: nowrap; }
                        img { width: 149px; }
                    </style>
                </head>
                <body>
                    <meta name="viewport" content="width=device-width; initial-scale=1.0">
                    <center><div class="wrapper">
                    <h1>Recently Added</h1>
            """
            
            if len(shows_html) > 0:
                html_content += f"""\
                        <table>
                            <tr><th colspan={int(config["mail"]["poster_colums"])}>TV-Shows</th></tr>
                            <tr>
                                {shows_html}
                            </tr>
                        </table>
                """
            if len(movies_html) > 0:
                html_content += f"""\
                    <table>
                        <tr><th colspan={int(config["mail"]["poster_colums"])}>Movies</th></tr>
                        <tr>
                            {movies_html}
                        </tr>
                    </table>
                """
            html_content += """\
                    </div></center>
                </body>
            </html>
            """
        
            print(plain_text)
            print(html_content)

            text_part = MIMEText(plain_text, 'plain')
            html_part = MIMEText(html_content, 'html')

            msg.attach(text_part)
            msg.attach(html_part)
            
            server.send_message(msg)


def check_recent_state():
    if os.path.exists(config["files"]["recent_state"]):
        modify_time = datetime.fromtimestamp(os.path.getmtime(config["files"]["recent_state"]))
        delta = datetime.now() - modify_time
        
        print(delta.total_seconds())
        
        if delta.total_seconds() >= config["mail"]["recent_interval"]:
            return True
    else:
        Path(config["files"]["recent_state"]).touch()
        return True
    
    return False



########################################################



sql_conn = sqlite3.connect(config["files"]["database"])
check_database(sql_conn)

get_recent_shows(sql_conn)
get_recent_movies(sql_conn)

send_mail(sql_conn)

#if check_recent_state():
#    send_mail(sql_conn)

sql_conn.commit()
sql_conn.close()





