#!/usr/bin/python3 
# Dependencies: python3-requests

import sqlite3
import os.path
import json
import smtplib, ssl
import configparser
from email.utils import formataddr
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText


config_file = 'config.ini'
basepath = os.path.dirname(os.path.abspath(__file__))

# Make sure the config file exists
if not os.path.exists(f'{basepath}/{config_file}'):
    print("Error: Cant find config!")
    exit(1)

config = configparser.ConfigParser()
config.read(f'{basepath}/{config_file}')

conn = sqlite3.connect(f'{basepath}/{config["files"]["database"]}')
cursor = conn.cursor()

# Login on SMTP server
context = ssl.create_default_context()

if config["mail"]["smtp_encryption_method"] == 'TLS':
    server = smtplib.SMTP(config["mail"]["smtp_host"], config["mail"]["smtp_port"])
    server.starttls(context=context) # Secure the connection with TLS

elif config["mail"]["smtp_encryption_method"] == 'SSL':
    server = smtplib.SMTP_SSL(config["mail"]["smtp_host"], config["mail"]["smtp_port"], context=context)

else:
    print("Error: Unknown encryption method!")
    exit(1)
    
server.login(config["mail"]["smtp_user"], config["mail"]["smtp_password"])
#---------------------------

for user_id, email in json.loads(config["api"]["user_ids"]).items():
    
    shows_rows = cursor.execute(f'SELECT series_name, series_id, server_id FROM shows WHERE user_id = "{user_id}" and timestamp > DATETIME("now", "-{config["mail"]["recent_interval"]} seconds") GROUP BY series_id ORDER BY timestamp, _id ASC LIMIT {config["mail"]["recent_limit"]};').fetchall();
    movies_rows = cursor.execute(f'SELECT name, id, server_id FROM movies WHERE user_id = "{user_id}" and timestamp > DATETIME("now", "-{config["mail"]["recent_interval"]} seconds") ORDER BY timestamp, _id ASC LIMIT {config["mail"]["recent_limit"]};').fetchall();
    
    shows_plain = ''
    shows_html = ''
    movies_plain = ''
    movies_html = ''
    
    columns = int(config["mail"]["poster_colums"])
    
    for count, show in enumerate(shows_rows):
        shows_plain += f"- {show[0]}\n"
        
        # Build the link to the clickable poster
        shows_html += f'<td><a href="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/web/index.html#!/item?id={show[1]}&serverId={show[2]}"><img src="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/emby/Items/{show[1]}/Images/Primary?maxHeight=494&amp;maxWidth=329&amp;quality=90"></a></td>'
        
        columns -= 1
        
        if columns <= 0 and count != len(shows_rows)-1: 
            columns = int(config["mail"]["poster_colums"])
            shows_html += f"</tr><tr>\n"
            
    # Make sure all columns in the last row have cells
    if columns != int(config["mail"]["poster_colums"]):
        for i in range(columns):
            shows_html += f"<td></td>\n"
    
    columns = int(config["mail"]["poster_colums"])
    
    for count, movie in enumerate(movies_rows):
        movies_plain += f"- {movie[0]}\n"
        
        # Build the link to the clickable poster
        movies_html += f'<td><a href="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/web/index.html#!/item?id={movie[1]}&serverId={movie[2]}"><img src="{config["api"]["protocol"]}://{config["api"]["host"]}:{config["api"]["port"]}/emby/Items/{movie[1]}/Images/Primary?maxHeight=494&amp;maxWidth=329&amp;quality=90"></a></td>\n'
        
        columns -= 1
        
        if columns <= 0 and count != len(shows_rows)-1: 
            columns = int(config["mail"]["poster_colums"])
            movies_html += f"</tr><tr>\n"
    
    # Make sure all columns in the last row have cells    
    if columns != int(config["mail"]["poster_colums"]):
        for i in range(columns):
            movies_html += f"<td></td>\n"
    
    # Dont send a mail if lists are empty
    if len(shows_rows) > 0 or len(movies_rows) > 0:
        msg = MIMEMultipart('alternative')
        msg['Subject'] = "Emby - Recently Added"
        msg['From'] = formataddr(('Emby Notification', config["mail"]["email_from"])) 
        msg['To'] = email
        
        # Plain-text version of content
        plain_text = f"Recently Added\n\n"
        if len(shows_plain) > 0:
            plain_text += f'TV-Shows\n{shows_plain}\n\n'
        
        if len(movies_plain) > 0:
            plain_text += f'Movies\n{movies_plain}\n'

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

        text_part = MIMEText(plain_text, 'plain')
        html_part = MIMEText(html_content, 'html')

        msg.attach(text_part)
        msg.attach(html_part)
        
        server.send_message(msg)




