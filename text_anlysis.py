from flask import Flask, render_template, request, redirect, url_for, session
import requests
from bs4 import BeautifulSoup
import nltk
from nltk.tokenize import sent_tokenize, word_tokenize
from nltk.corpus import stopwords
import psycopg2
import json
import re
from authlib.integrations.flask_client import OAuth



app = Flask(__name__)

conn = psycopg2.connect(
        dbname="textanalysis",
        user="postgres",
        password="manupal",
        host="localhost",
        port=7250
    )

@app.route("/")
def home():
    return render_template("index.html",analysis = None)

@app.route("/check",methods=["POST","GET"])
def check():
    if request.method== 'POST':
        url = request.form["url"]
        page = requests.get(url)
        soup = BeautifulSoup(page.content, "html.parser")
        cur = conn.cursor()
        headline=soup.find('h1').text
        sub_heading=soup.find('h2', class_="synopsis").text
        c=soup.find('div',id="pcl-full-content")
        d=c.find_all('blockquote')
        for i in d:
             i.decompose()

        text=c.find_all('p')


        Cleaned_text = ''
        for p_tag in text:
            Cleaned_text += p_tag.get_text().strip()

        # Clean the main content: remove extra newlines and whitespace
        content = re.sub(r'\n+', '\n', Cleaned_text)
        content = re.sub(r'\s+', ' ', Cleaned_text)
        
        
    

        # stopword = stopwords.words('english')
        x = sent_tokenize(content)
        sent_count=len(x)
        dict1 = {}
        sent = 0
        word = 0
        for i in x:
            sent += 1
            word_list = word_tokenize(i) 
            word = word+len(word_list)
            x = nltk.pos_tag(word_list, tagset='universal')
            for i in x:
                if i[1] in dict1:
                    dict1[i[1]] += 1
                else:
                    dict1[i[1]] = 1

        with open("dict1.json", 'w'):
                # Use json.dump() to write the dictionary to the file
                    a = json.dumps(dict1)
        # cur.execute("select * from news_data")
        # news_data = cur.fetchone()
        # if not news_data:
    # Create the table if it does not exist
        cur = conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS news_data (
                id SERIAL PRIMARY KEY,
                url VARCHAR(255) NOT NULL,
                no_of_words INT,
                no_of_sentences INT,
                cleantext TEXT,
                post_tags TEXT
            )
        """)
            # Commit the changes
    
        # else:
        #     return f'It is not returning get method'

        cur.execute(
            "INSERT INTO news_data (url,no_of_words,no_of_sentences, cleantext, post_tags) VALUES (%s, %s, %s, %s, %s)", (url, word, sent_count, content, a))
        
        conn.commit()
        cur.close()
        return render_template('analysis.html',url=url, word=word, sent_count=sent_count, content=content, a=a,headline=headline,   sub_heading=sub_heading)
    
@app.route("/verify", methods = ["GET","POST"])
def verify():
     return render_template("admin.html")
@app.route("/validate", methods = ["GET","POST"])
def validate():
     cur = conn.cursor()
     p = "1234"
     password = request.form["password"]
     if request.method == "POST":
        if p == password:
            cur.execute('''SELECT * FROM news_data''')
            rows = cur.fetchall()
            data_dict = []
            for row in rows:
                analysis_dict = {
                "url": row[1], 
                "no_of_words": row[2],  
                "no_of_sentences": row[3], 
                "cleantext": row[4],
                "post_tags": row[5]
                }
                data_dict.append(analysis_dict)
            return render_template("url.html", data_dict=data_dict)

        else:
            return render_template("admin.html")
        

oauth = OAuth(app)

app.config['SECRET_KEY'] = "my_secret_key"
app.config['GITHUB_CLIENT_ID'] = "e6023ca0003fbaa42a36"
app.config['GITHUB_CLIENT_SECRET'] = "8a732e7beed6d3cee29767d788be94160f59634b"

github = oauth.register(
    name='github',
    client_id=app.config["GITHUB_CLIENT_ID"],
    client_secret=app.config["GITHUB_CLIENT_SECRET"],
    access_token_url='https://github.com/login/oauth/access_token',
    access_token_params=None,
    authorize_url='https://github.com/login/oauth/authorize',
    authorize_params=None,
    api_base_url='https://api.github.com/',
    client_kwargs={'scope': 'user:email'},
)

# GitHub admin usernames for verification
github_admin_usernames = ["MANUPAL4321", "atmabodha"]

# Default route
@app.route('/admin_route')
def admin_route():
    is_admin = False
    github_token = session.get('github_token')
    if github_token:
        github = oauth.create_client('github')
        resp = github.get('user').json()
        username = resp.get('login')
        if username in github_admin_usernames:
            is_admin = True
    return render_template('admin.html', logged_in=github_token is not None, is_admin=is_admin)


# Github login route
@app.route('/login/github')
def github_login():
    github = oauth.create_client('github')
    redirect_uri = url_for('github_authorize', _external=True)
    return github.authorize_redirect(redirect_uri)

@app.route('/login/github/authorize')
def github_authorize():
    github = oauth.create_client('github')
    token = github.authorize_access_token()
    session['github_token'] = token
    resp = github.get('user').json()
    print(f"\n{resp}\n")

    if 'login' in resp:
        username = resp['login']
        if username in github_admin_usernames:
            cur = conn.cursor()
            cur.execute('''SELECT * FROM news_data''')
            rows = cur.fetchall()
            data_dict = []
            for row in rows:
                analysis_dict = {
                "url": row[1], 
                "no_of_words": row[2],  
                "no_of_sentences": row[3], 
                "cleantext": row[4],
                "post_tags": row[5]
                }
                data_dict.append(analysis_dict)
            return render_template("url.html", data_dict=data_dict)

        else:
            return f'you are not authorized to access this page'
    else:
        return f'Unable to fetch github username'


if __name__=='__main__':
    app.run(debug=True)
    conn.close()