import requests
from bs4 import BeautifulSoup
import re
import json
import csv
from datetime import datetime

# Configuration
FILTERED = False
BASE_URL = "https://infoterre.brgm.fr/rechercher/pagine.htm"
JSESSIONID = "D002D4FEFBF302B74FB354D558379680"
HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Cookie": f"JSESSIONID={JSESSIONID}"
}
BASE_FILE_NAME = "output/details_results"

def get_unique_filename(base_name, extension):
    """
    Generates a unique filename using the base name and a timestamp.
    """
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    return f"{base_name}_{timestamp}.{extension}"

json_filename = get_unique_filename(BASE_FILE_NAME, "json")
csv_filename = get_unique_filename(BASE_FILE_NAME, "csv")


def get_session_id():
    session = requests.Session()
    session.get("https://infoterre.brgm.fr/rechercher/")
    if 'JSESSIONID' in session.cookies:
        JSESSIONID = session.cookies['JSESSIONID']
        print(f"Session ID récupéré: {JSESSIONID}")
        HEADERS["Cookie"] = f"JSESSIONID={JSESSIONID}"
        return JSESSIONID
    else:
        raise Exception("Impossible de récupérer le JSESSIONID.")

def launch_research():
    url = "https://infoterre.brgm.fr/rechercher/default.htm;jsessionid=" + JSESSIONID
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        url = "https://infoterre.brgm.fr/rechercher/switch.htm?scope=6"
        response = requests.get(url, headers=HEADERS)
        if response.status_code == 200:
            url = "https://infoterre.brgm.fr/rechercher/search.htm"
            response = requests.post(url, headers=HEADERS, data={"inValues": "0", "scopeValue": "6", "what": "", "where": "", "carmatSubstance": "", "carmatProduit": "", "carmatGidic": "", "x": "19", "y": "8"})
            if response.status_code == 200:
                print("Recherche lancée avec succès.")
        else:
            raise Exception(f"Erreur lors du lancement de la recherche: {response.status_code}")
    else:
        raise Exception(f"Erreur lors du lancement de la recherche: {response.status_code}")

def apply_filter():
    url = "https://infoterre.brgm.fr/rechercher/refine.htm"
    data = {"action": "refine", "id": "carmat_actif:true"}
    response = requests.post(url, headers=HEADERS, data=data)
    if response.status_code == 200:
        print("Filtre appliqué avec succès.")
    else:
        raise Exception(f"Erreur lors de l'application du filtre: {response.status_code}")



def fetch_page_content(page_number=1):
    """
    Envoie une requête POST pour récupérer le contenu d'une page spécifique.
    """
    data = {"page": str(page_number)}
    response = requests.post(BASE_URL, headers=HEADERS, data=data)

    if response.status_code == 200:
        print(f"Page {page_number} récupérée avec succès.")
        return response.text
    else:
        print(f"Erreur lors de la récupération de la page {page_number}: {response.status_code}")
        return None


def get_max_pages(html_content):
    """
    Récupère le nombre maximum de pages à partir du contenu HTML.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    pagination_element = soup.find("span", id="pagination_last")
    if pagination_element:
        match = re.search(r"value\s*=\s*'(\d+)'", pagination_element.get("onclick", ""))
        if match:
            return int(match.group(1))
    print("Nombre maximum de pages introuvable, valeur par défaut utilisée (1).")
    return 1


def extract_field(tr_element, label):
    """
    Récupère la valeur d'un champ dans un <tr> en fonction du label fourni.
    """
    field = tr_element.find("font", text=lambda t: t and label in t)
    if field and field.find_next_sibling("font", class_="results_item_field_value"):
        return field.find_next_sibling("font", class_="results_item_field_value").text.strip()
    return None


def fetch_additional_details(carmat_id):
    """
    Fetch additional details for a given Carmat ID.
    """
    url = f"https://www.mineralinfo.fr/Fiches/carmat/{carmat_id}"
    response = requests.get(url, headers=HEADERS)
    if response.status_code == 200:
        print(f"Détails supplémentaires récupérés pour ID {carmat_id}.")
        return response.text
    else:
        print(f"Erreur lors de la récupération des détails pour ID : {carmat_id}: {response.status_code}")
        return None


def extract_most_recent_ap(html_content):
    """
    Extracts the most recent AP (Arrêté préfectoral) information from the given HTML content.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    historique_section = soup.find("div", id="historique")

    if not historique_section:
        print("Section 'historique' introuvable.")
        return None

    ap_table = historique_section.find("table", class_="table table-bordered")
    if not ap_table:
        print("Tableau AP introuvable dans la section 'historique'.")
        return None

    rows = ap_table.find_all("tr")[1:]  # Skip the header row
    ap_data = []

    for row in rows:
        cols = row.find_all("td")
        if len(cols) < 6:
            continue

        try:
            ap_type = cols[1].text.strip()
            start_date = datetime.strptime(cols[2].text.strip(), "%Y-%m-%d")
            end_date = cols[3].text.strip()
            end_date = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
            volume_kt = cols[4].text.strip() or None
            volume_m3 = cols[5].text.strip() or None

            ap_data.append({
                "Type": ap_type,
                "Date début validité": start_date,
                "Date fin validité": end_date,
                "Volume total (kt)": volume_kt,
                "Volume total (m³)": volume_m3
            })
        except ValueError:
            continue

    if not ap_data:
        return None

    return max(ap_data, key=lambda x: x["Date début validité"])


def extract_additional_data(soup, row_id):
    """
    Récupère les données additionnelles pour une ligne spécifique, identifiée par son ID.
    """
    additional_row = soup.find("tr", id=f"results_item_additional_content_{row_id}_null")
    if not additional_row:
        return {}

    additional_data = {
        "Site en activité": extract_field(additional_row, "Site en activité"),
        "Exploitation en eau": extract_field(additional_row, "Exploitation en eau"),
        "Substances": extract_field(additional_row, "Substances"),
        "Produits": extract_field(additional_row, "Produits"),
        "Longitude": extract_field(additional_row, "Longitude"),
        "Latitude": extract_field(additional_row, "Latitude"),
        "Date de fin d'autorisation": extract_field(additional_row, "Date de fin d'autorisation")
    }
    return additional_data


def extract_results(html_content):
    """
    Analyse le contenu HTML pour extraire les données principales et additionnelles.
    """
    soup = BeautifulSoup(html_content, "html.parser")
    results = []

    main_rows = soup.find_all("tr", class_="results_item")
    for row in main_rows:
        result = {}

        id_element = row.find("a", {"id": lambda x: x and x.startswith("chkItem_")})
        if id_element:
            row_id = id_element["id"].split("_")[1]
            result["Identifiant"] = extract_field(row, "Identifiant")
            result["Numéro S3IC"] = extract_field(row, "Numéro S3IC")
            result["Commune"] = extract_field(row, "Commune")

            additional_data = extract_additional_data(soup, row_id)
            result.update(additional_data)

            details_html = fetch_additional_details(row_id.strip('carmat'))
            if details_html:
                recent_ap = extract_most_recent_ap(details_html)
                if recent_ap:
                    result.update(recent_ap)

            results.append(result)

    return results


def custom_serializer(obj):
    """
    Sérialise les objets non pris en charge par défaut, comme datetime.
    """
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Type {type(obj)} non sérialisable.")

def fetch_all_results():
    """
    Parcourt toutes les pages dynamiquement et récupère toutes les données des résultats.
    Les résultats sont enregistrés dans un fichier JSON, puis convertis en CSV à la fin.
    """
    first_page_content = fetch_page_content()
    max_pages = get_max_pages(first_page_content)
    print(f"Nombre maximum de pages détecté : {max_pages}")

    # Initialize the JSON file
    with open(json_filename, "w", encoding="utf-8") as json_file:
        json_file.write("[")

    results_buffer = []  # Buffer to hold results temporarily
    dump_interval = 10  # Save every `dump_interval` pages

    try:
        for page_number in range(1, max_pages + 1):
            html_content = fetch_page_content(page_number)
            if html_content:
                results = extract_results(html_content)
                results_buffer.extend(results)

            # Periodically dump results to JSON
            if page_number % dump_interval == 0 or page_number == max_pages:
                with open(json_filename, "a", encoding="utf-8") as json_file:
                    for result in results_buffer:
                        json.dump(result, json_file, ensure_ascii=False, indent=4, default=custom_serializer)
                        json_file.write(",\n")  # Add comma between JSON objects
                results_buffer.clear()  # Clear buffer to free memory
                print(f"Résultats des pages jusqu'à {page_number} sauvegardés.")

        # Remove trailing comma and close the JSON array
        with open(json_filename, "rb+") as json_file:
            json_file.seek(0, 2)  # Move to the end of the file
            json_file.seek(json_file.tell() - 2, 0)  # Remove last comma
            json_file.write(b"]")

    except Exception as e:
        print(f"Erreur : {e}")
        # Ensure the JSON array is closed if there's an error
        with open(json_filename, "a", encoding="utf-8") as json_file:
            json_file.write("]")
        raise

    print(f"Résultats sauvegardés dans {json_filename}.")
    return json_filename


def convert_json_to_csv():
    """
    Convertit les données d'un fichier JSON en fichier CSV.
    """
    try:
        with open(json_filename, "r", encoding="utf-8") as json_file:
            data = json.load(json_file)

        if not data:
            print("Aucune donnée à convertir en CSV.")
            return

        # Collect all unique keys
        all_fieldnames = set()
        for result in data:
            all_fieldnames.update(result.keys())

        # Write to CSV
        with open(csv_filename, "w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(csv_file, fieldnames=sorted(all_fieldnames))  # Sort keys for consistent order
            writer.writeheader()
            writer.writerows(data)

        print(f"Résultats convertis en CSV et sauvegardés dans {csv_filename}.")
    except Exception as e:
        print(f"Erreur lors de la conversion JSON -> CSV : {e}")


# Main
if __name__ == "__main__":
    try:
        get_session_id()
        launch_research()

        if FILTERED:
            print("Filtrage des résultats...")
            apply_filter()

        json_file = fetch_all_results()
        convert_json_to_csv()

    except Exception as e:
        print(f"Erreur : {e}")