from flask import Flask, request, render_template_string
import requests
from bs4 import BeautifulSoup
from datetime import datetime

app = Flask(__name__)

def get_street_web_address(street_name):
    print(f"Suche nach Straße: {street_name}")
    url = f"https://www.ebwo.de/de/abfallkalender/2024/?sTerm={street_name}"
    print(f"Such-URL: {url}")
    
    response = requests.get(url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')

    # Find the <li> element with the street link
    list_entries = soup.find_all('li', class_='listEntryObject-news')
    print(f"{len(list_entries)} Listeneinträge gefunden")

    for entry in list_entries:
        if street_name.lower() in entry.get_text(strip=True).lower():
            street_url = entry.get('data-url')
            if street_url:
                full_street_url = f"https://www.ebwo.de{street_url}"
                print(f"Straßen-URL gefunden: {full_street_url}")
                return full_street_url
    
    print(f"Kein Link für Straße gefunden: {street_name}")
    return None

def get_abholtermine(street_url):
    print(f"Abholtermine abrufen von: {street_url}")
    response = requests.get(street_url)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    abholtermine = {
        "Gelbe Tonne": [],
        "Altpapier": [],
        "Restabfall (bis 240 Liter)": [],
        "Bio-Abfälle": []
    }

    # Extract dates from all relevant divs
    divs = soup.find_all('div', style=lambda value: value and 'margin-top:25px;' in value)
    current_category = None
    category_order = ["Gelbe Tonne", "Altpapier", "Restabfall (bis 240 Liter)", "Bio-Abfälle"]

    for idx, div in enumerate(divs):
        # Assign category based on the current index in the order
        current_category = category_order[idx % len(category_order)]
        div_content = div.get_text(separator="\n").split("\n")
        dates = [d.strip() for d in div_content if d.strip() and d.strip().isdigit() == False and d.strip().count('.') == 2]
        
        abholtermine[current_category].extend(dates)

    # Sort dates within each category
    for category in abholtermine:
        abholtermine[category] = sorted(abholtermine[category], key=lambda date: datetime.strptime(date, "%d.%m.%Y"))

    print(f"Abholtermine gefunden: {abholtermine}")
    return abholtermine

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        street_name = request.form['street_name']
        print(f"Formular mit Straßenname eingereicht: {street_name}")
        street_url = get_street_web_address(street_name)
        if street_url:
            abholtermine = get_abholtermine(street_url)
            return render_template_string(TEMPLATE, street_name=street_name, abholtermine=abholtermine)
        else:
            error = "Straße nicht gefunden. Bitte versuchen Sie es erneut."
            print(error)
            return render_template_string(TEMPLATE, error=error)
    return render_template_string(TEMPLATE)

TEMPLATE = '''
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
          <form method="post">
            <div class="form-group">
              <label for="street_name">Straßenname</label>
              <input type="text" class="form-control" id="street_name" name="street_name" required>
            </div>
            <button type="submit" class="btn btn-primary">Abholtermine finden</button>
          </form>
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