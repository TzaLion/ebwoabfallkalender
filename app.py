from flask import Flask, redirect, url_for, session, request, jsonify, render_template_string
from authlib.integrations.flask_client import OAuth
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)
app.secret_key = '4c3d2e1f0a9b8c7d6e5f4g3h2i1j0k9l'  # Replace with your own secret key

# OIDC configuration
client_id = "306a6d10-0a7f-47b6-bae3-75a0c851526e"
client_secret = "5ccf1d06-13d5-4d82-a0af-ca729686130a"
discovery_url = "https://idp.mycityapp.cloud.test.kobil.com/auth/realms/worms/.well-known/openid-configuration"

oauth = OAuth(app)
oidc_client = oauth.register(
    name='oidc',
    client_id=client_id,
    client_secret=client_secret,
    server_metadata_url=discovery_url,
    client_kwargs={
        'scope': 'openid profile email',
    }
)

def get_street_web_address(street_name):
    url = f"https://www.ebwo.de/de/abfallkalender/2024/?sTerm={street_name}"
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    list_entries = soup.find_all('li', class_='listEntryObject-news')
    for entry in list_entries:
        if street_name.lower() in entry.get_text(strip=True).lower():
            street_url = entry.get('data-url')
            if street_url:
                return f"https://www.ebwo.de{street_url}"
    return None

def get_abholtermine(street_url):
    response = requests.get(street_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    abholtermine = {
        "Gelbe Tonne": [],
        "Altpapier": [],
        "Restabfall (bis 240 Liter)": [],
        "Bio-Abfälle": []
    }

    divs = soup.find_all('div', style=lambda value: value and 'margin-top:25px;' in value)
    category_order = ["Gelbe Tonne", "Altpapier", "Restabfall (bis 240 Liter)", "Bio-Abfälle"]

    for idx, div in enumerate(divs):
        current_category = category_order[idx % len(category_order)]
        div_content = div.get_text(separator="\n").split("\n")
        dates = [d.strip() for d in div_content if d.strip() and d.strip().isdigit() == False and d.strip().count('.') == 2]
        
        abholtermine[current_category].extend(dates)

    for category in abholtermine:
        abholtermine[category] = sorted(abholtermine[category], key=lambda date: datetime.strptime(date, "%d.%m.%Y"))

    return abholtermine

@app.route('/test')
def test():
    return "Test route is working"

@app.route('/oidc')
def oidc():
    redirect_uri = url_for('oidc_callback', _external=True)
    return oidc_client.authorize_redirect(redirect_uri)

@app.route('/oidc/callback')
def oidc_callback():
    token = oidc_client.authorize_access_token()
    user_info = oidc_client.parse_id_token(token)
    
    street_name = user_info.get('address')
    if not street_name:
        return "Address not found in user attributes", 400

    street_url = get_street_web_address(street_name)
    if street_url:
        abholtermine = get_abholtermine(street_url)
        return render_template_string(OIDC_TEMPLATE, street_name=street_name, abholtermine=abholtermine)
    else:
        return "Street not found. Please try again.", 404

OIDC_TEMPLATE = '''
<!doctype html>
<html lang="de">
  <head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1, shrink-to-fit=no">
    <link href="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/css/bootstrap.min.css" rel="stylesheet">
    <title>Abholtermine Finder</title>
  </head>
  <body>
    <div class="container mt-5">
      <div class="card">
        <div class="card-header">
          <h1>Abholtermine Finder</h1>
        </div>
        <div class="card-body">
          {% if abholtermine %}
            <h2 class="mt-4">Abholtermine für {{ street_name }}</h2>
            {% for category, dates in abholtermine.items() %}
              <h3>{{ category }}</h3>
              <ul class="list-group mt-3">
                {% for date in dates %}
                  <li class="list-group-item">{{ date }}</li>
                {% endfor %}
              </ul>
            {% endfor %}
          {% endif %}
          {% if error %}
            <div class="alert alert-danger mt-3">{{ error }}</div>
          {% endif %}
        </div>
      </div>
    </div>
    <script src="https://code.jquery.com/jquery-3.5.1.slim.min.js"></script>
    <script src="https://cdn.jsdelivr.net/npm/@popperjs/core@2.9.2/dist/umd/popper.min.js"></script>
    <script src="https://stackpath.bootstrapcdn.com/bootstrap/4.5.2/js/bootstrap.min.js"></script>
  </body>
</html>
'''

if __name__ == '__main__':
    app.run(debug=True)